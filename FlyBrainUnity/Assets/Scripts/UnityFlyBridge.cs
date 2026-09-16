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
        PresentationClutterSystem clutter;
        Transform flyProxy;
        Transform flyVisual;
        Transform originMarker;
        GameObject flyForwardIndicator;
        Renderer[] flyRenderers;
        VisualPrefabLibrary visuals;
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
        Bounds flyRendererBounds;
        float substrateTopY;
        float visualGroundGap;
        Vector3 flyVisualBaseLocalPosition;
        float visualGroundingCorrection;
        bool visualGroundingCalibrated;
        bool runtimeHierarchyLogged;
        bool debugVisualization = true;
        float overviewFieldOfView;
        Vector3 overviewTarget, overviewTargetGoal, overviewTargetVelocity;
        float overviewYaw, overviewPitch, overviewDistance;
        float overviewYawGoal, overviewPitchGoal, overviewDistanceGoal;
        float overviewYawVelocity, overviewPitchVelocity, overviewDistanceVelocity;
        float followYaw, followPitch = 20f, followDistance;
        float followYawGoal, followPitchGoal = 20f, followDistanceGoal;
        float followYawVelocity, followPitchVelocity, followDistanceVelocity;
        float targetSmoothTime;
        float lastLeftClickTime = -10f;
        bool cameraHelpVisible;
        bool overviewHasManualFocus;
        bool environmentDefinitionReceived;
        bool flyMaterialsValid;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if (FindFirstObjectByType<UnityFlyBridge>() == null)
                new GameObject("Python Fly Bridge").AddComponent<UnityFlyBridge>();
        }

        void Awake()
        {
            DontDestroyOnLoad(gameObject);
            visuals = VisualPrefabLibrary.LoadOrDefault();
            BuildFly();
            BuildOriginMarker();
            environment = new UnityEnvironmentManager(transform, visuals);
            clutter = new PresentationClutterSystem(transform, environment, visuals, targetPosition);
            sceneCamera = Camera.main;
            if (sceneCamera == null)
            {
                var cameraObject = new GameObject("Fly Bridge Camera");
                sceneCamera = cameraObject.AddComponent<Camera>();
                cameraObject.tag = "MainCamera";
            }
            sceneCamera.nearClipPlane = .01f;
            sceneCamera.clearFlags = CameraClearFlags.SolidColor;
            sceneCamera.backgroundColor = new Color(.16f, .18f, .17f);
            overviewFieldOfView = sceneCamera.fieldOfView;
            followDistance = followDistanceGoal = Mathf.Sqrt(visuals.followDistance * visuals.followDistance +
                visuals.followHeight * visuals.followHeight);
            followPitch = followPitchGoal = Mathf.Atan2(visuals.followHeight, visuals.followDistance) * Mathf.Rad2Deg;
            cameraHelpVisible = visuals.showCameraHelp;
            ConfigurePresentationLighting();
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
                        environmentDefinitionReceived = true;
                        TryGenerateClutter();
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
            UpdateVisualGrounding();
            var keyboard = Keyboard.current;
            if (keyboard != null && keyboard.fKey.wasPressedThisFrame) ToggleCameraMode();
            if (keyboard != null && keyboard.dKey.wasPressedThisFrame) SetDebugVisualization(!debugVisualization);
            if (keyboard != null && keyboard.hKey.wasPressedThisFrame) cameraHelpVisible = !cameraHelpVisible;
            if (keyboard != null && keyboard.cKey.wasPressedThisFrame) clutter.Toggle();
            if (keyboard != null && keyboard.homeKey.wasPressedThisFrame) ResetOverview();
            if (keyboard != null && keyboard.spaceKey.wasPressedThisFrame)
            {
                cameraMode = CameraMode.Overview;
                FocusOverview(flyProxy.position);
            }
            ReadCameraInput();
            UpdateCamera();
            environment.FaceLabels(sceneCamera);
            UpdateVisibilityDiagnostics();
            var elapsed = Time.unscaledTime - rateWindowStarted;
            if (elapsed >= 1f) { updatesPerSecond = receivedThisWindow / elapsed; receivedThisWindow = 0; rateWindowStarted = Time.unscaledTime; }
        }

        void TryGenerateClutter()
        {
            if (!environmentDefinitionReceived) return;
            if (visuals == null || visuals.ClutterPrefabCount == 0)
            {
                Debug.LogError("[FlyBrain Clutter] Environment is ready, but the loaded library has zero valid prefabs; generation is deferred.");
                return;
            }
            clutter.Regenerate();
        }

        void ToggleCameraMode()
        {
            cameraMode = cameraMode == CameraMode.Overview ? CameraMode.FollowFly : CameraMode.Overview;
        }

        void ReadCameraInput()
        {
            var mouse = Mouse.current;
            if (mouse == null || sceneCamera == null) return;
            var delta = mouse.delta.ReadValue();
            var scroll = mouse.scroll.ReadValue().y;
            if (cameraMode == CameraMode.Overview)
            {
                if (mouse.rightButton.isPressed)
                {
                    overviewYawGoal += delta.x * visuals.orbitSensitivity;
                    overviewPitchGoal = Mathf.Clamp(overviewPitchGoal - delta.y * visuals.orbitSensitivity,
                        visuals.minimumPitch, visuals.maximumPitch);
                }
                if (mouse.middleButton.isPressed)
                {
                    var scale = overviewDistanceGoal * visuals.panSensitivity;
                    overviewTargetGoal += (-sceneCamera.transform.right * delta.x - sceneCamera.transform.up * delta.y) * scale;
                    targetSmoothTime = visuals.cameraSmoothTime;
                }
                if (scroll != 0f) overviewDistanceGoal = ZoomDistance(overviewDistanceGoal, scroll, OverviewMinimumDistance);
                if (mouse.leftButton.wasPressedThisFrame)
                {
                    if (Time.unscaledTime - lastLeftClickTime <= .3f) FocusUnderPointer(mouse.position.ReadValue());
                    lastLeftClickTime = Time.unscaledTime;
                }
            }
            else
            {
                if (mouse.rightButton.isPressed)
                {
                    followYawGoal += delta.x * visuals.orbitSensitivity;
                    followPitchGoal = Mathf.Clamp(followPitchGoal - delta.y * visuals.orbitSensitivity,
                        visuals.minimumPitch, visuals.maximumPitch);
                }
                if (scroll != 0f) followDistanceGoal = ZoomDistance(followDistanceGoal, scroll, visuals.minimumFollowDistance);
            }
        }

        float ZoomDistance(float currentDistance, float scrollDelta, float minimumDistance)
        {
            // Input System reports a notch as 120 on some platforms and 1 on
            // others. Preserve fractional high-resolution wheel/trackpad input.
            var notches = Mathf.Abs(scrollDelta) >= 10f ? scrollDelta / 120f : scrollDelta;
            var factorPerNotch = 1f + visuals.zoomPercentagePerNotch * .01f;
            return ClampDistance(currentDistance * Mathf.Pow(factorPerNotch, -notches), minimumDistance);
        }

        float OverviewMinimumDistance => overviewHasManualFocus
            ? visuals.minimumFocusDistance : visuals.minimumOverviewDistance;

        float ClampDistance(float value, float minimumDistance) =>
            Mathf.Clamp(value, minimumDistance, visuals.maximumZoomDistance);

        void FocusUnderPointer(Vector2 screenPoint)
        {
            var ray = sceneCamera.ScreenPointToRay(screenPoint);
            var found = environment.Raycast(ray, out var point);
            var closest = found ? Vector3.Distance(ray.origin, point) : float.PositiveInfinity;
            foreach (var renderer in flyRenderers)
                if (renderer != null && renderer.bounds.IntersectRay(ray, out var distance) && distance < closest)
                { point = flyProxy.position; closest = distance; found = true; }
            if (found) FocusOverview(point);
        }

        void FocusOverview(Vector3 point)
        {
            overviewHasManualFocus = true;
            overviewTargetGoal = point;
            targetSmoothTime = visuals.focusTransitionTime;
        }

        void ResetOverview()
        {
            if (!environment.IsSynchronized) return;
            environment.RefreshBounds();
            cameraMode = CameraMode.Overview;
            overviewHasManualFocus = false;
            FrameOverview(false);
            targetSmoothTime = visuals.focusTransitionTime;
        }

        void UpdateCamera()
        {
            if (sceneCamera == null) return;
            if (cameraMode == CameraMode.FollowFly)
            {
                SmoothFollowState();
                var lookTarget = flyProxy.position + flyProxy.forward * visuals.lookAheadDistance + Vector3.up * .06f;
                ApplyCamera(lookTarget, flyProxy.eulerAngles.y + followYaw, followPitch, followDistance);
                sceneCamera.fieldOfView = visuals.followFieldOfView;
            }
            else if (environment.IsSynchronized)
            {
                sceneCamera.fieldOfView = overviewFieldOfView;
                if (cameraNeedsFrame) FrameOverview(true);
                SmoothOverviewState();
                ApplyCamera(overviewTarget, overviewYaw, overviewPitch, overviewDistance);
            }
        }

        void FrameOverview(bool immediate)
        {
            var bounds = environment.Bounds;
            bounds.Encapsulate(latest == null ? flyProxy.position : targetPosition);
            foreach (var renderer in flyRenderers) if (renderer != null) bounds.Encapsulate(renderer.bounds);
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
            overviewTargetGoal = bounds.center;
            overviewDistanceGoal = ClampDistance(distance * 1.15f, visuals.minimumOverviewDistance);
            overviewYawGoal = Mathf.Atan2(-outward.x, -outward.z) * Mathf.Rad2Deg;
            overviewPitchGoal = Mathf.Asin(outward.y) * Mathf.Rad2Deg;
            if (immediate)
            {
                overviewTarget = overviewTargetGoal;
                overviewDistance = overviewDistanceGoal;
                overviewYaw = overviewYawGoal;
                overviewPitch = overviewPitchGoal;
            }
            cameraNeedsFrame = false;
        }

        void SmoothOverviewState()
        {
            var seconds = targetSmoothTime > 0f ? targetSmoothTime : visuals.cameraSmoothTime;
            overviewTarget = Vector3.SmoothDamp(overviewTarget, overviewTargetGoal, ref overviewTargetVelocity,
                seconds, Mathf.Infinity, Time.unscaledDeltaTime);
            overviewYaw = Mathf.SmoothDampAngle(overviewYaw, overviewYawGoal, ref overviewYawVelocity,
                visuals.cameraSmoothTime, Mathf.Infinity, Time.unscaledDeltaTime);
            overviewPitch = Mathf.SmoothDampAngle(overviewPitch, overviewPitchGoal, ref overviewPitchVelocity,
                visuals.cameraSmoothTime, Mathf.Infinity, Time.unscaledDeltaTime);
            overviewDistance = Mathf.SmoothDamp(overviewDistance, overviewDistanceGoal, ref overviewDistanceVelocity,
                visuals.cameraSmoothTime, Mathf.Infinity, Time.unscaledDeltaTime);
            if ((overviewTarget - overviewTargetGoal).sqrMagnitude < .000001f) targetSmoothTime = 0f;
        }

        void SmoothFollowState()
        {
            followYaw = Mathf.SmoothDampAngle(followYaw, followYawGoal, ref followYawVelocity,
                visuals.cameraSmoothTime, Mathf.Infinity, Time.unscaledDeltaTime);
            followPitch = Mathf.SmoothDampAngle(followPitch, followPitchGoal, ref followPitchVelocity,
                visuals.cameraSmoothTime, Mathf.Infinity, Time.unscaledDeltaTime);
            followDistance = Mathf.SmoothDamp(followDistance, followDistanceGoal, ref followDistanceVelocity,
                visuals.cameraSmoothTime, Mathf.Infinity, Time.unscaledDeltaTime);
        }

        void ApplyCamera(Vector3 target, float yaw, float pitch, float distance)
        {
            var minimumDistance = cameraMode == CameraMode.FollowFly
                ? visuals.minimumFollowDistance : OverviewMinimumDistance;
            distance = ClampDistance(distance, minimumDistance);
            var orbit = Quaternion.Euler(pitch, yaw, 0f);
            var desired = target + orbit * (Vector3.back * distance);
            // Keep the lens just above the substrate without imposing a game-scale
            // clearance that pushes a manually focused macro view away from the fly.
            var nearClip = Mathf.Clamp(distance * .015f, .0001f, .05f);
            if (environment.IsSynchronized)
                desired.y = Mathf.Max(desired.y, environment.GroundSurfaceY + nearClip * 1.25f);
            sceneCamera.transform.SetPositionAndRotation(desired,
                Quaternion.LookRotation(target - desired, Vector3.up));
            sceneCamera.nearClipPlane = nearClip;
            sceneCamera.farClipPlane = Mathf.Max(100f, distance + environment.Bounds.extents.magnitude * 3f);
        }

        void UpdateVisibilityDiagnostics()
        {
            if (sceneCamera == null || flyProxy == null) return;
            viewportPosition = sceneCamera.WorldToViewportPoint(flyProxy.position);
            var planes = GeometryUtility.CalculateFrustumPlanes(sceneCamera);
            flyRendererBounds = CombinedRendererBounds();
            flyInFrustum = GeometryUtility.TestPlanesAABB(planes, flyRendererBounds);
            flyFloorClearance = flyProxy.position.y - environment.GroundSurfaceY;
            if (environment.TryGetSurfaceBelow(flyProxy.position, out var surfaceY)) substrateTopY = surfaceY;
            visualGroundGap = flyRendererBounds.min.y - substrateTopY;
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
            flyVisual = new GameObject("Fly Visual (presentation offsets only)").transform;
            flyVisual.SetParent(flyProxy, false);
            flyVisual.localPosition = visuals.fly.modelPositionOffset;
            flyVisualBaseLocalPosition = visuals.fly.modelPositionOffset;
            flyVisual.localRotation = Quaternion.Euler(visuals.fly.modelRotationOffset);
            flyVisual.localScale = visuals.fly.modelScale;
            if (visuals.fly.prefab != null)
            {
                var model = Instantiate(visuals.fly.prefab, flyVisual, false); model.name = "Custom Fly Model";
                foreach (var collider in model.GetComponentsInChildren<Collider>()) Destroy(collider);
            }
            else
            {
            // Geometry is offset above the authoritative thorax transform, not the
            // transform itself. This prevents a low-spawned fly from being buried
            // in the floor while preserving every scientific coordinate exactly.
            Part(PrimitiveType.Sphere, "Orange body", flyVisual, new Vector3(0, .07f, 0),
                new Vector3(.18f, .13f, .32f), new Color(1f, .32f, .015f));
            Part(PrimitiveType.Sphere, "Red head", flyVisual, new Vector3(0, .075f, .19f),
                new Vector3(.15f, .14f, .15f), Color.red);
            flyForwardIndicator = Part(PrimitiveType.Cube, "Cyan forward indicator", flyVisual, new Vector3(0, .12f, .37f),
                new Vector3(.045f, .045f, .34f), Color.cyan);
            }
            flyRenderers = flyProxy.GetComponentsInChildren<Renderer>();
            flyMaterialsValid = FlyMaterialValidation.Validate(flyRenderers, out var materialReason);
            Debug.Log($"[Fly Materials] {(flyMaterialsValid ? "OK" : "MISSING/INVALID")}: {materialReason}");
        }

        Bounds CombinedRendererBounds()
        {
            var bounds = new Bounds(flyProxy == null ? Vector3.zero : flyProxy.position, Vector3.zero);
            var initialized = false;
            foreach (var renderer in flyRenderers ?? Array.Empty<Renderer>())
                if (renderer != null && renderer.enabled)
                {
                    if (!initialized) { bounds = renderer.bounds; initialized = true; }
                    else bounds.Encapsulate(renderer.bounds);
                }
            return bounds;
        }

        void UpdateVisualGrounding()
        {
            if (flyVisual == null) return;
            // Rebuild the child presentation position in world-up space so a
            // pitched authoritative root cannot tilt the grounding correction.
            flyVisual.localPosition = flyVisualBaseLocalPosition;
            if (!visuals.fly.autoGroundVisual || environment?.IsSynchronized != true) return;
            if (!visualGroundingCalibrated && latest != null &&
                (flyProxy.position - targetPosition).sqrMagnitude < .000001f &&
                environment.TryGetSurfaceBelow(flyProxy.position, out var surfaceY) &&
                flyProxy.position.y - surfaceY <= visuals.fly.maximumGroundingRootHeight)
            {
                var bottomY = CombinedRendererBounds().min.y;
                visualGroundingCorrection = surfaceY + visuals.fly.groundingOffset - bottomY;
                visualGroundingCalibrated = true;
                Debug.Log($"[Fly Visual Grounding] child-only correction {visualGroundingCorrection:F4}; " +
                    $"authoritative root Y {flyProxy.position.y:F4}, visual bottom Y {bottomY:F4}, substrate top Y {surfaceY:F4}");
            }
            if (visualGroundingCalibrated)
            {
                var baseWorldPosition = flyProxy.TransformPoint(flyVisualBaseLocalPosition);
                flyVisual.position = baseWorldPosition + Vector3.up * visualGroundingCorrection;
            }
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
            originMarker = new GameObject("Origin axes (X red, Y green, Z blue)").transform; originMarker.SetParent(transform, false);
            Part(PrimitiveType.Cube, "Unity X", originMarker, new Vector3(.3f, 0, 0), new Vector3(.6f, .025f, .025f), Color.red);
            Part(PrimitiveType.Cube, "Unity Y", originMarker, new Vector3(0, .3f, 0), new Vector3(.025f, .6f, .025f), Color.green);
            Part(PrimitiveType.Cube, "Unity Z", originMarker, new Vector3(0, 0, .3f), new Vector3(.025f, .025f, .6f), Color.blue);
        }

        void SetDebugVisualization(bool visible)
        {
            debugVisualization = visible;
            if (originMarker != null) originMarker.gameObject.SetActive(visible);
            if (flyForwardIndicator != null) flyForwardIndicator.SetActive(visible);
            environment?.SetDebugVisible(visible);
        }

        void DrawGroundingDebug()
        {
            if (!debugVisualization || flyProxy == null || !environment.IsSynchronized) return;
            clutter?.DrawGroundingDebug();
            const float size = .08f;
            DrawCross(flyProxy.position, size, Color.magenta);
            var bottom = new Vector3(flyRendererBounds.center.x, flyRendererBounds.min.y, flyRendererBounds.center.z);
            DrawCross(bottom, size, Color.cyan);
            var surface = new Vector3(flyProxy.position.x, substrateTopY, flyProxy.position.z);
            Debug.DrawLine(surface - Vector3.right * size * 2f, surface + Vector3.right * size * 2f, Color.yellow);
            Debug.DrawLine(surface - Vector3.forward * size * 2f, surface + Vector3.forward * size * 2f, Color.yellow);
        }

        static void DrawCross(Vector3 point, float size, Color color)
        {
            Debug.DrawLine(point - Vector3.right * size, point + Vector3.right * size, color);
            Debug.DrawLine(point - Vector3.up * size, point + Vector3.up * size, color);
            Debug.DrawLine(point - Vector3.forward * size, point + Vector3.forward * size, color);
        }

        static void ConfigurePresentationLighting()
        {
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(.23f, .27f, .29f);
            RenderSettings.ambientEquatorColor = new Color(.14f, .15f, .13f);
            RenderSettings.ambientGroundColor = new Color(.055f, .045f, .035f);
            RenderSettings.ambientIntensity = .85f;
            RenderSettings.reflectionIntensity = .75f;
            foreach (var light in FindObjectsByType<Light>(FindObjectsSortMode.None))
                if (light.type == LightType.Directional) { light.color = new Color(1f, .92f, .78f); light.intensity = 1.35f; light.shadows = LightShadows.Soft; }
            var fillObject = new GameObject("Presentation Fill Light");
            var fill = fillObject.AddComponent<Light>(); fill.type = LightType.Directional;
            fill.color = new Color(.55f, .68f, .8f); fill.intensity = .32f; fill.shadows = LightShadows.None;
            fillObject.transform.rotation = Quaternion.Euler(35f, 145f, 0f);
        }

        void OnGUI()
        {
            DrawGroundingDebug();
            if (debugVisualization)
            {
                var raw = latest == null ? "--" : $"[{receivedPosition.x:F2}, {receivedPosition.y:F2}, {receivedPosition.z:F2}] mm";
                var converted = latest == null ? "--" : $"[{targetPosition.x:F3}, {targetPosition.y:F3}, {targetPosition.z:F3}]";
                var rendererActive = flyRenderers != null && Array.Exists(flyRenderers, r => r != null && r.enabled && r.gameObject.activeInHierarchy);
                var text = $"Python: {(connected ? "Connected" : "Disconnected")}\n" +
                $"Simulation time: {(latest == null ? "--" : latest.time.ToString("F3"))} s\nState rate: {updatesPerSecond:F1} Hz\n" +
                $"Raw Python fly position: {raw}\nConverted Unity fly position: {converted}\n" +
                $"Fly GameObject active: {(flyProxy != null && flyProxy.gameObject.activeInHierarchy ? "yes" : "no")}\n" +
                $"Fly renderer active: {(rendererActive ? "yes" : "no")}\n" +
                $"Fly materials: {(flyMaterialsValid ? "OK" : "MISSING/INVALID")}\nEnvironment sync: {(environment?.IsSynchronized == true ? "yes" : "no")}\n" +
                $"Environment object count: {environment?.ObjectCount ?? 0}/{environment?.DefinitionObjectCount ?? 0}\nCamera mode: {cameraMode} (F to switch)\n" +
                $"Fly root/body world: {flyProxy?.position.ToString() ?? "--"} / {(flyRenderers != null && flyRenderers.Length > 0 ? flyRenderers[0].transform.position.ToString() : "--")}\n" +
                $"Fly root/body scale: {flyProxy?.localScale.ToString() ?? "--"} / {(flyRenderers != null && flyRenderers.Length > 0 ? flyRenderers[0].transform.localScale.ToString() : "--")}\n" +
                $"Fly viewport: [{viewportPosition.x:F2}, {viewportPosition.y:F2}, depth {viewportPosition.z:F2}] in frustum: {(flyInFrustum ? "yes" : "NO")}\n" +
                $"Camera pos/fwd: {sceneCamera?.transform.position.ToString() ?? "--"} / {sceneCamera?.transform.forward.ToString() ?? "--"}\n" +
                $"Camera clip/distance: {sceneCamera?.nearClipPlane:F3}..{sceneCamera?.farClipPlane:F3} / {(sceneCamera == null ? 0 : Vector3.Distance(sceneCamera.transform.position, flyProxy.position)):F3}\n" +
                $"Fly root Y: {flyProxy.position.y:F4}\n" +
                $"Fly visual root Y: {flyVisual.position.y:F4}\n" +
                $"Fly visual bottom Y: {flyRendererBounds.min.y:F4}\n" +
                $"Fly visual top Y: {flyRendererBounds.max.y:F4}\n" +
                $"Substrate top Y: {substrateTopY:F4}\n" +
                $"Visual ground gap: {visualGroundGap:F4} units\n" +
                $"Fly root vs floor: {flyFloorClearance:F3} units\nScientific debug: on (D to toggle)\n" +
                $"Visual scale: 1 mm = {WorldVisualScale.UnityUnitsPerMillimetre:g} Unity units\n" +
                $"Clutter: {(clutter?.Visible == true ? "ON" : "OFF")}\nClutter objects: {clutter?.ObjectCount ?? 0}\n" +
                $"Clutter library loaded: {(clutter?.LibraryLoaded == true ? "YES" : "NO")}\nClutter prefab count: {clutter?.PrefabCount ?? 0}\n" +
                $"Substrate ready: {(clutter?.SubstrateReady == true ? "YES" : "NO")}\nGeneration attempted: {(clutter?.GenerationAttempted == true ? "YES" : "NO")}\n" +
                $"Generation result: {clutter?.ObjectCount ?? 0}\nLast clutter error: {clutter?.LastError ?? "not initialized"}\n" +
                $"Rocks: {clutter?.Count("Rocks") ?? 0}  Leaves: {clutter?.Count("Leaves") ?? 0}  Twigs: {clutter?.Count("Twigs") ?? 0}\n" +
                $"Organic Debris: {clutter?.Count("Organic Debris") ?? 0}  Large Vegetation: {clutter?.Count("Large Vegetation") ?? 0}\n" +
                $"Micro Debris: {clutter?.Count("Micro Debris") ?? 0}\n" +
                ClutterWarnings() +
                $"Clutter seed: {visuals.clutterSeed}\nBehavior: {latest?.behavior ?? "--"}";
                GUI.Box(new Rect(12, 12, 680, 735), text);
            }
            if (cameraHelpVisible)
            {
                const string help = "CAMERA / PRESENTATION\nRight Drag     Orbit\nMiddle Drag    Pan\nScroll         Zoom\nDouble Click   Focus Object\nSpace          Focus Fly\nHome           Reset View\nF              Follow Fly\nC              Toggle Clutter\nD              Debug View\nH              Hide Help";
                GUI.Box(new Rect(Screen.width - 225, 12, 213, 216), help);
            }
        }

        string ClutterWarnings()
        {
            if (clutter == null) return string.Empty;
            var result = string.Empty;
            foreach (var category in new[] { "Rocks", "Leaves", "Twigs", "Organic Debris", "Large Vegetation", "Micro Debris" })
                if (clutter.ShouldWarn(category)) result += $"WARNING: {category} generated 0\n";
            return result;
        }

        /// <summary>Editor hook; rebuilds presentation instances without touching authoritative state.</summary>
        public void RegeneratePresentationClutter() => clutter?.Regenerate();

        void OnDestroy() { cancellation?.Cancel(); cancellation?.Dispose(); clutter?.Clear(); environment?.Clear(); }
    }
}
