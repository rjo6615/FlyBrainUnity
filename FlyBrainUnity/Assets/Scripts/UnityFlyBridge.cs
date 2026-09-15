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
    /// <summary>Non-blocking TCP receiver and independently rendered fly proxy.</summary>
    public sealed class UnityFlyBridge : MonoBehaviour
    {
        [SerializeField] private string host = "127.0.0.1";
        [SerializeField] private int port = 8765;
        [SerializeField, Min(0.01f)] private float interpolationSeconds = 0.08f;

        private readonly ConcurrentQueue<FlyStateMessage> incoming = new();
        private CancellationTokenSource cancellation;
        private Transform flyProxy;
        private Vector3 targetPosition;
        private Quaternion targetRotation = Quaternion.identity;
        private volatile bool connected;
        private FlyStateMessage latest;
        private float updatesPerSecond;
        private int receivedThisWindow;
        private float rateWindowStarted;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Install()
        {
            if (FindFirstObjectByType<UnityFlyBridge>() != null) return;
            new GameObject("Python Fly Bridge").AddComponent<UnityFlyBridge>();
        }

        private void Awake()
        {
            DontDestroyOnLoad(gameObject);
            BuildProofOfConceptScene();
            rateWindowStarted = Time.unscaledTime;
            cancellation = new CancellationTokenSource();
            _ = ReceiveLoop(cancellation.Token);
        }

        private void Update()
        {
            while (incoming.TryDequeue(out var message))
            {
                latest = message;
                targetPosition = FlyGymCoordinates.Position(message.position);
                targetRotation = FlyGymCoordinates.Orientation(message.orientation);
                receivedThisWindow++;
            }

            var blend = 1f - Mathf.Exp(-Time.unscaledDeltaTime / interpolationSeconds);
            flyProxy.SetPositionAndRotation(
                Vector3.Lerp(flyProxy.position, targetPosition, blend),
                Quaternion.Slerp(flyProxy.rotation, targetRotation, blend));

            var elapsed = Time.unscaledTime - rateWindowStarted;
            if (elapsed >= 1f)
            {
                updatesPerSecond = receivedThisWindow / elapsed;
                receivedThisWindow = 0;
                rateWindowStarted = Time.unscaledTime;
            }
        }

        private async Task ReceiveLoop(CancellationToken token)
        {
            while (!token.IsCancellationRequested)
            {
                try
                {
                    using var client = new TcpClient();
                    await client.ConnectAsync(host, port);
                    connected = true;
                    using var reader = new StreamReader(
                        client.GetStream(), Encoding.UTF8, false, 4096, leaveOpen: false);
                    while (!token.IsCancellationRequested)
                    {
                        var line = await reader.ReadLineAsync();
                        if (line == null) break;
                        var message = JsonUtility.FromJson<FlyStateMessage>(line);
                        if (message != null && message.IsValid)
                        {
                            // Bound latency if rendering was paused: newest wins.
                            while (incoming.Count >= 2) incoming.TryDequeue(out _);
                            incoming.Enqueue(message);
                        }
                    }
                }
                catch (OperationCanceledException) { }
                catch (Exception) when (!token.IsCancellationRequested)
                {
                    // Status is shown in the HUD; reconnect quietly rather than
                    // flooding the console while Python is not running.
                }
                finally
                {
                    connected = false;
                }

                if (!token.IsCancellationRequested)
                    await Task.Delay(1000, token);
            }
        }

        private void BuildProofOfConceptScene()
        {
            var body = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            body.name = "Authoritative Fly Proxy";
            body.transform.SetParent(transform, false);
            body.transform.localScale = new Vector3(0.004f, 0.008f, 0.004f);
            body.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
            body.GetComponent<Renderer>().material.color = new Color(0.12f, 0.08f, 0.03f);
            flyProxy = transform;

            if (Camera.main != null)
            {
                Camera.main.transform.position = new Vector3(0f, 0.09f, -0.14f);
                Camera.main.transform.LookAt(new Vector3(0f, 0.005f, 0f));
            }
        }

        private void OnGUI()
        {
            var position = latest == null ? "--" :
                $"[{latest.position[0]:F2}, {latest.position[1]:F2}, {latest.position[2]:F2}] mm";
            var text = $"Python: {(connected ? "Connected" : "Disconnected")}\n" +
                       $"Simulation time: {(latest == null ? "--" : latest.time.ToString("F3"))} s\n" +
                       $"Fly position: {position}\n" +
                       $"Behavior: {latest?.behavior ?? "--"}\n" +
                       $"State rate: {updatesPerSecond:F1} Hz";
            GUI.Box(new Rect(12, 12, 310, 118), text);
        }

        private void OnDestroy()
        {
            cancellation?.Cancel();
            cancellation?.Dispose();
        }
    }
}
