using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

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
                    if (definition.IsValid) { environment.ApplyDefinition(definition); cameraNeedsFrame = true; }
                }
                else if (header.type == "environment_state")
                    environment.ApplyState(JsonUtility.FromJson<EnvironmentState>(json));
            }

            var blend = 1f - Mathf.Exp(-Time.unscaledDeltaTime / interpolationSeconds);
            flyProxy.SetPositionAndRotation(Vector3.Lerp(flyProxy.position, targetPosition, blend),
                Quaternion.Slerp(flyProxy.rotation, targetRotation, blend));
            if (Input.GetKeyDown(KeyCode.F)) cameraMode = cameraMode == CameraMode.Overview
                ? CameraMode.FollowFly : CameraMode.Overview;
            if (Input.GetKeyDown(KeyCode.L)) environment.ToggleLabels();
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
                foreach (var renderer in flyRenderers) if (renderer != null) bounds.Encapsulate(renderer.bounds);
                var radius = Mathf.Max(.5f, bounds.extents.magnitude);
                var halfVertical = sceneCamera.fieldOfView * Mathf.Deg2Rad * .5f;
                var halfHorizontal = Mathf.Atan(Mathf.Tan(halfVertical) * Mathf.Max(.1f, sceneCamera.aspect));
                var limitingAngle = Mathf.Min(halfVertical, halfHorizontal);
                var distance = radius / Mathf.Sin(limitingAngle) * 1.18f;
                var direction = new Vector3(.82f, 1.05f, -1f).normalized;
                var desired = bounds.center + direction * distance;
                sceneCamera.transform.position = cameraNeedsFrame
                    ? desired : Vector3.Lerp(sceneCamera.transform.position, desired, blend);
                sceneCamera.transform.LookAt(bounds.center);
                sceneCamera.nearClipPlane = Mathf.Max(.01f, radius / 1000f);
                sceneCamera.farClipPlane = distance + radius * 3f;
                cameraNeedsFrame = false;
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
                        while (incoming.Count >= 8) incoming.TryDequeue(out _);
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
            Part(PrimitiveType.Sphere, "Contrasting head", flyProxy, new Vector3(0, .075f, .19f),
                new Vector3(.15f, .14f, .15f), new Color(1f, .88f, .3f));
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
                $"Fly viewport: [{viewportPosition.x:F2}, {viewportPosition.y:F2}, depth {viewportPosition.z:F2}] in frustum: {(flyInFrustum ? "yes" : "NO")}\n" +
                $"Fly vs floor surface: {flyFloorClearance:F3} units\nLabels: {(environment?.LabelsVisible == true ? "on" : "off")} (L to toggle)\n" +
                $"Visual scale: 1 mm = {WorldVisualScale.UnityUnitsPerMillimetre:g} Unity units\nBehavior: {latest?.behavior ?? "--"}";
            GUI.Box(new Rect(12, 12, 470, 330), text);
        }

        void OnDestroy() { cancellation?.Cancel(); cancellation?.Dispose(); environment?.Clear(); }
    }
}
