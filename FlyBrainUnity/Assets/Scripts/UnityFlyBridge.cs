using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.InputSystem;

namespace FlyBrain.UnityBridge
{
    /// <summary>Output-only TCP receiver, environment mirror, camera, and diagnostics.</summary>
    public sealed class UnityFlyBridge : MonoBehaviour
    {
        enum CameraMode { Overview, FollowFly }
        [SerializeField] string host = "127.0.0.1";
        [SerializeField] int port = 8765;
        [SerializeField, Min(.01f)] float interpolationSeconds = .08f;
        readonly ConcurrentQueue<string> incoming = new();
        CancellationTokenSource cancellation;
        UnityEnvironmentManager environment;
        Transform flyProxy;
        Renderer[] flyRenderers;
        Camera sceneCamera;
        Vector3 targetPosition;
        Quaternion targetRotation = Quaternion.identity;
        volatile bool connected;
        FlyStateMessage latest;
        float updatesPerSecond, rateWindowStarted;
        int receivedThisWindow;
        CameraMode cameraMode = CameraMode.Overview;
        bool cameraNeedsFrame = true;
        Vector3 receivedPosition;
        Vector3 viewportPosition;
        bool flyInFrustum;
        float flyFloorClearance;
        bool runtimeHierarchyLogged;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if (FindFirstObjectByType<UnityFlyBridge>() == null)
                new GameObject("Python Fly Bridge").AddComponent<UnityFlyBridge>();
        }

        void Awake()
        {
            DontDestroyOnLoad(gameObject);
            BuildFly();
            BuildOriginMarker();
            environment = new UnityEnvironmentManager(transform);
            sceneCamera = Camera.main;
            if (sceneCamera == null)
            {
                var cameraObject = new GameObject("Fly Bridge Camera");
                sceneCamera = cameraObject.AddComponent<Camera>();
                cameraObject.tag = "MainCamera";
            }
            sceneCamera.nearClipPlane = .01f;
            rateWindowStarted = Time.unscaledTime;
            cancellation = new CancellationTokenSource();
            _ = ReceiveLoop(cancellation.Token);
        }

        void Update()
        {
            while (incoming.TryDequeue(out var json))
            {
                var header = JsonUtility.FromJson<MessageHeader>(json);
                if (header == null || header.protocol_version != 1) continue;
                if (header.type == "fly_state")
                {
                    var message = JsonUtility.FromJson<FlyStateMessage>(json);
                    if (!message.IsValid) continue;
                    latest = message;
                    receivedPosition = new Vector3(message.position[0], message.position[1], message.position[2]);
                    targetPosition = WorldVisualScale.Position(message.position);
                    targetRotation = WorldVisualScale.Orientation(message.orientation);
                    receivedThisWindow++;
                }
                else if (header.type == "environment_definition")
                {
                    var definition = JsonUtility.FromJson<EnvironmentDefinition>(json);
                    if (definition.IsValid)
                    {
                        environment.ApplyDefinition(definition);
                        cameraNeedsFrame = true;
                        runtimeHierarchyLogged = false;
                    }
                }
                else if (header.type == "environment_state")
                    environment.ApplyState(JsonUtility.FromJson<EnvironmentState>(json));
            }

            var blend = 1f - Mathf.Exp(-Time.unscaledDeltaTime / interpolationSeconds);
            flyProxy.SetPositionAndRotation(Vector3.Lerp(flyProxy.position, targetPosition, blend),
                Quaternion.Slerp(flyProxy.rotation, targetRotation, blend));
            var keyboard = Keyboard.current;
            if (keyboard != null && keyboard.fKey.wasPressedThisFrame) cameraMode = cameraMode == CameraMode.Overview
                ? CameraMode.FollowFly : CameraMode.Overview;
            if (keyboard != null && keyboard.lKey.wasPressedThisFrame) environment.ToggleLabels();
            UpdateCamera(blend);
            environment.FaceLabels(sceneCamera);
            UpdateVisibilityDiagnostics();
            var elapsed = Time.unscaledTime - rateWindowStarted;
            if (elapsed >= 1f) { updatesPerSecond = receivedThisWindow / elapsed; receivedThisWindow = 0; rateWindowStarted = Time.unscaledTime; }
        }

        void UpdateCamera(float blend)
        {
            if (sceneCamera == null) return;
            if (cameraMode == CameraMode.FollowFly)
            {
                var desired = flyProxy.position - flyProxy.forward * 1.15f + Vector3.up * .85f;
                sceneCamera.transform.position = Vector3.Lerp(sceneCamera.transform.position, desired, blend);
                sceneCamera.transform.LookAt(flyProxy.position + Vector3.up * .06f);
                sceneCamera.farClipPlane = 100f;
            }
            else if (environment.IsSynchronized)
            {
                var bounds = environment.Bounds;
                // targetPosition is the newest authoritative pose; interpolation
                // must not make initial framing depend on the proxy's old origin.
                bounds.Encapsulate(latest == null ? flyProxy.position : targetPosition);
                foreach (var renderer in flyRenderers) if (renderer != null) bounds.Encapsulate(renderer.bounds);
                if (cameraNeedsFrame)
                {
                    // Fit all eight authoritative AABB corners for this elevated
                    // direction instead of approximating them with a sphere.
                    var outward = new Vector3(.8f, 1.15f, -1f).normalized;
                    var rotation = Quaternion.LookRotation(-outward, Vector3.up);
                    var inverse = Quaternion.Inverse(rotation);
                    var tanVertical = Mathf.Tan(sceneCamera.fieldOfView * Mathf.Deg2Rad * .5f);
                    var tanHorizontal = tanVertical * Mathf.Max(.1f, sceneCamera.aspect);
                    var distance = .1f;
                    for (var x = -1; x <= 1; x += 2)
                    for (var y = -1; y <= 1; y += 2)
                    for (var z = -1; z <= 1; z += 2)
                    {
                        var corner = bounds.center + Vector3.Scale(bounds.extents, new Vector3(x, y, z));
                        var local = inverse * (corner - bounds.center);
                        distance = Mathf.Max(distance, Mathf.Abs(local.x) / tanHorizontal - local.z);
                        distance = Mathf.Max(distance, Mathf.Abs(local.y) / tanVertical - local.z);
                    }
                    distance *= 1.15f;
                    sceneCamera.transform.SetPositionAndRotation(bounds.center + outward * distance, rotation);
                    sceneCamera.nearClipPlane = Mathf.Max(.01f, distance - bounds.extents.magnitude * 1.25f);
                    sceneCamera.farClipPlane = distance + bounds.extents.magnitude * 2f;
                    cameraNeedsFrame = false;
                }
            }
        }

        void UpdateVisibilityDiagnostics()
        {
            if (sceneCamera == null || flyProxy == null) return;
            viewportPosition = sceneCamera.WorldToViewportPoint(flyProxy.position);
            var planes = GeometryUtility.CalculateFrustumPlanes(sceneCamera);
            var bounds = flyRenderers != null && flyRenderers.Length > 0
                ? flyRenderers[0].bounds : new Bounds(flyProxy.position, Vector3.zero);
            for (var i = 1; flyRenderers != null && i < flyRenderers.Length; i++) bounds.Encapsulate(flyRenderers[i].bounds);
            flyInFrustum = GeometryUtility.TestPlanesAABB(planes, bounds);
            flyFloorClearance = flyProxy.position.y - environment.GroundSurfaceY;
            if (!runtimeHierarchyLogged && latest != null && environment.IsSynchronized)
            {
                var body = flyRenderers != null && flyRenderers.Length > 0 ? flyRenderers[0] : null;
                Debug.Log("[Unity Fly Runtime]\n" +
                    $"Root world position: {flyProxy.position}\n" +
                    $"Body world position: {(body == null ? "--" : body.transform.position.ToString())}\n" +
                    $"Root localScale: {flyProxy.localScale}\n" +
                    $"Body localScale: {(body == null ? "--" : body.transform.localScale.ToString())}\n" +
                    $"Renderer bounds center: {(body == null ? "--" : body.bounds.center.ToString())}\n" +
                    $"Renderer bounds size: {(body == null ? "--" : body.bounds.size.ToString())}\n" +
                    $"Camera world position: {sceneCamera.transform.position}\n" +
                    $"Camera forward: {sceneCamera.transform.forward}\n" +
                    $"Camera clip: {sceneCamera.nearClipPlane:F3} .. {sceneCamera.farClipPlane:F3}\n" +
                    $"Camera distance to fly: {Vector3.Distance(sceneCamera.transform.position, flyProxy.position):F3}\n" +
                    $"Fly viewport: {viewportPosition}");
                runtimeHierarchyLogged = true;
            }
        }

        async Task ReceiveLoop(CancellationToken token)
        {
            while (!token.IsCancellationRequested)
            {
                try
                {
                    using var client = new TcpClient(); await client.ConnectAsync(host, port); connected = true;
                    using var reader = new StreamReader(client.GetStream(), Encoding.UTF8, false, 4096, false);
                    while (!token.IsCancellationRequested)
                    {
                        var line = await reader.ReadLineAsync(); if (line == null) break;
                        // Definitions are ordered protocol messages. Dropping the
                        // oldest entry here could discard the one definition while
                        // retaining later fly states, so let the main thread drain.
                        incoming.Enqueue(line);
                    }
                }
                catch (OperationCanceledException) { }
                catch (Exception) when (!token.IsCancellationRequested) { }
                finally { connected = false; }
                if (!token.IsCancellationRequested) await Task.Delay(1000, token);
            }
        }

        void BuildFly()
        {
            flyProxy = new GameObject("Authoritative Fly Proxy").transform;
            flyProxy.SetParent(transform, false);
            // Geometry is offset above the authoritative thorax transform, not the
            // transform itself. This prevents a low-spawned fly from being buried
            // in the floor while preserving every scientific coordinate exactly.
            Part(PrimitiveType.Sphere, "Orange body", flyProxy, new Vector3(0, .07f, 0),
                new Vector3(.18f, .13f, .32f), new Color(1f, .32f, .015f));
            Part(PrimitiveType.Sphere, "Red head", flyProxy, new Vector3(0, .075f, .19f),
                new Vector3(.15f, .14f, .15f), Color.red);
            Part(PrimitiveType.Cube, "Cyan forward indicator", flyProxy, new Vector3(0, .12f, .37f),
                new Vector3(.045f, .045f, .34f), Color.cyan);
            flyRenderers = flyProxy.GetComponentsInChildren<Renderer>();
        }

        static GameObject Part(PrimitiveType type, string name, Transform parent, Vector3 position,
            Vector3 scale, Color color)
        {
            var go = GameObject.CreatePrimitive(type); go.name = name; go.transform.SetParent(parent, false);
            go.transform.localPosition = position; go.transform.localScale = scale;
            Destroy(go.GetComponent<Collider>());
            var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            go.GetComponent<Renderer>().material = new Material(shader) { color = color };
            return go;
        }

        void BuildOriginMarker()
        {
            var root = new GameObject("Origin axes (X red, Y green, Z blue)").transform; root.SetParent(transform, false);
            Part(PrimitiveType.Cube, "Unity X", root, new Vector3(.3f, 0, 0), new Vector3(.6f, .025f, .025f), Color.red);
            Part(PrimitiveType.Cube, "Unity Y", root, new Vector3(0, .3f, 0), new Vector3(.025f, .6f, .025f), Color.green);
            Part(PrimitiveType.Cube, "Unity Z", root, new Vector3(0, 0, .3f), new Vector3(.025f, .025f, .6f), Color.blue);
        }

        void OnGUI()
        {
            var raw = latest == null ? "--" : $"[{receivedPosition.x:F2}, {receivedPosition.y:F2}, {receivedPosition.z:F2}] mm";
            var converted = latest == null ? "--" : $"[{targetPosition.x:F3}, {targetPosition.y:F3}, {targetPosition.z:F3}]";
            var rendererActive = flyRenderers != null && Array.Exists(flyRenderers, r => r != null && r.enabled && r.gameObject.activeInHierarchy);
            var text = $"Python: {(connected ? "Connected" : "Disconnected")}\n" +
                $"Simulation time: {(latest == null ? "--" : latest.time.ToString("F3"))} s\nState rate: {updatesPerSecond:F1} Hz\n" +
                $"Raw Python fly position: {raw}\nConverted Unity fly position: {converted}\n" +
                $"Fly GameObject active: {(flyProxy != null && flyProxy.gameObject.activeInHierarchy ? "yes" : "no")}\n" +
                $"Fly renderer active: {(rendererActive ? "yes" : "no")}\nEnvironment sync: {(environment?.IsSynchronized == true ? "yes" : "no")}\n" +
                $"Environment object count: {environment?.ObjectCount ?? 0}/{environment?.DefinitionObjectCount ?? 0}\nCamera mode: {cameraMode} (F to switch)\n" +
                $"Fly root/body world: {flyProxy?.position.ToString() ?? "--"} / {(flyRenderers != null && flyRenderers.Length > 0 ? flyRenderers[0].transform.position.ToString() : "--")}\n" +
                $"Fly root/body scale: {flyProxy?.localScale.ToString() ?? "--"} / {(flyRenderers != null && flyRenderers.Length > 0 ? flyRenderers[0].transform.localScale.ToString() : "--")}\n" +
                $"Fly viewport: [{viewportPosition.x:F2}, {viewportPosition.y:F2}, depth {viewportPosition.z:F2}] in frustum: {(flyInFrustum ? "yes" : "NO")}\n" +
                $"Camera pos/fwd: {sceneCamera?.transform.position.ToString() ?? "--"} / {sceneCamera?.transform.forward.ToString() ?? "--"}\n" +
                $"Camera clip/distance: {sceneCamera?.nearClipPlane:F3}..{sceneCamera?.farClipPlane:F3} / {(sceneCamera == null ? 0 : Vector3.Distance(sceneCamera.transform.position, flyProxy.position)):F3}\n" +
                $"Fly vs floor surface: {flyFloorClearance:F3} units\nLabels: {(environment?.LabelsVisible == true ? "on" : "off")} (L to toggle)\n" +
                $"Visual scale: 1 mm = {WorldVisualScale.UnityUnitsPerMillimetre:g} Unity units\nBehavior: {latest?.behavior ?? "--"}";
            GUI.Box(new Rect(12, 12, 620, 410), text);
        }

        void OnDestroy() { cancellation?.Cancel(); cancellation?.Dispose(); environment?.Clear(); }
    }
}
