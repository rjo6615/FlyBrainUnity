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
            UpdateCamera(blend);
            var elapsed = Time.unscaledTime - rateWindowStarted;
            if (elapsed >= 1f) { updatesPerSecond = receivedThisWindow / elapsed; receivedThisWindow = 0; rateWindowStarted = Time.unscaledTime; }
        }

        void UpdateCamera(float blend)
        {
            if (sceneCamera == null) return;
            if (cameraMode == CameraMode.FollowFly)
            {
                var desired = flyProxy.position - flyProxy.forward * 2.4f + Vector3.up * 1.6f;
                sceneCamera.transform.position = Vector3.Lerp(sceneCamera.transform.position, desired, blend);
                sceneCamera.transform.LookAt(flyProxy.position + Vector3.up * .15f);
                sceneCamera.farClipPlane = 100f;
            }
            else if (cameraNeedsFrame && environment.IsSynchronized)
            {
                var bounds = environment.Bounds;
                var radius = Mathf.Max(1f, bounds.extents.magnitude);
                sceneCamera.transform.position = bounds.center + new Vector3(0, radius * 1.35f, -radius * 1.2f);
                sceneCamera.transform.LookAt(bounds.center);
                sceneCamera.nearClipPlane = Mathf.Max(.01f, radius / 1000f);
                sceneCamera.farClipPlane = radius * 8f;
                cameraNeedsFrame = false;
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
            var body = Part(PrimitiveType.Capsule, "Body", flyProxy, Vector3.zero,
                new Vector3(.22f, .42f, .22f), new Color(.95f, .55f, .06f));
            body.transform.localRotation = Quaternion.Euler(90, 0, 0);
            Part(PrimitiveType.Sphere, "Head", flyProxy, new Vector3(0, .03f, .28f),
                new Vector3(.25f, .22f, .22f), new Color(.15f, .04f, .02f));
            // Bright forward cone-like pointer (a slender cube) along local +Z.
            Part(PrimitiveType.Cube, "Forward indicator", flyProxy, new Vector3(0, .13f, .55f),
                new Vector3(.06f, .06f, .55f), Color.cyan);
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
            var raw = latest == null ? "--" : $"[{latest.position[0]:F2}, {latest.position[1]:F2}, {latest.position[2]:F2}] mm";
            var converted = latest == null ? "--" : $"[{targetPosition.x:F3}, {targetPosition.y:F3}, {targetPosition.z:F3}]";
            var rendererActive = flyRenderers != null && Array.Exists(flyRenderers, r => r != null && r.enabled && r.gameObject.activeInHierarchy);
            var text = $"Python: {(connected ? "Connected" : "Disconnected")}\n" +
                $"Simulation time: {(latest == null ? "--" : latest.time.ToString("F3"))} s\nState rate: {updatesPerSecond:F1} Hz\n" +
                $"Raw Python fly position: {raw}\nConverted Unity fly position: {converted}\n" +
                $"Fly GameObject active: {(flyProxy != null && flyProxy.gameObject.activeInHierarchy ? "yes" : "no")}\n" +
                $"Fly renderer active: {(rendererActive ? "yes" : "no")}\nEnvironment sync: {(environment?.IsSynchronized == true ? "yes" : "no")}\n" +
                $"Environment object count: {environment?.ObjectCount ?? 0}\nCamera mode: {cameraMode} (F to switch)\n" +
                $"Visual scale: 1 mm = {WorldVisualScale.UnityUnitsPerMillimetre:g} Unity units\nBehavior: {latest?.behavior ?? "--"}";
            GUI.Box(new Rect(12, 12, 430, 252), text);
        }

        void OnDestroy() { cancellation?.Cancel(); cancellation?.Dispose(); environment?.Clear(); }
    }
}
