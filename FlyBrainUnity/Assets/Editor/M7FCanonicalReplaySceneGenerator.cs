using FlyBrain.M7FReplay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

public static class M7FCanonicalReplaySceneGenerator
{
    [MenuItem("Fly Brain/M7F/Create Canonical Replay Scene")]
    public static void CreateCanonicalReplayScene()
    {
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var top = new GameObject("M7F Canonical Replay");
        top.AddComponent<M7FCanonicalReplayPresentation>();
        var replaySystem = Child(top.transform, "ReplaySystem");
        var loader = replaySystem.gameObject.AddComponent<M7FReplayLoader>();
        var controller = replaySystem.gameObject.AddComponent<M7FReplayController>();
        var ui = replaySystem.gameObject.AddComponent<M7FScientificUI>();

        var environment = Child(top.transform, "Environment");
        var ground = GameObject.CreatePrimitive(PrimitiveType.Plane); ground.name = "VisualGround — PRESENTATION REFERENCE ONLY"; ground.transform.SetParent(environment, false); ground.transform.localScale = Vector3.one * .8f;
        Object.DestroyImmediate(ground.GetComponent<Collider>());

        var enabled = BuildFly(top.transform, "EnabledFlyRoot — NEURAL MOTOR ENABLED");
        var disabled = BuildFly(top.transform, "DisabledFlyRoot — MATCHED MOTOR-DISABLED CONTROL");
        controller.Configure(loader, enabled, disabled);
        ui.Configure(controller);

        var cameraRig = Child(top.transform, "CameraRig"); var cameraObject = Child(cameraRig, "Main Camera"); cameraObject.tag = "MainCamera";
        var camera = cameraObject.gameObject.AddComponent<Camera>(); camera.nearClipPlane = .01f; camera.farClipPlane = 100f;
        cameraObject.gameObject.AddComponent<AudioListener>(); cameraObject.gameObject.AddComponent<M7FReplayCamera>().Configure(top.transform, M7FScientificFlyBuilder.ApproximateVisualRadius * 2f);

        var lighting = Child(top.transform, "Lighting"); var lightObject = Child(lighting, "Directional Light"); var light = lightObject.gameObject.AddComponent<Light>(); light.type = LightType.Directional; light.intensity = 1.1f; lightObject.rotation = Quaternion.Euler(45, -35, 0);
        AddLabel(top.transform, "CONTACT IDENTITY UNAVAILABLE", new Vector3(0, 1.5f, 0));
        EditorSceneManager.MarkSceneDirty(scene); Selection.activeGameObject = top;
        Debug.Log("Created M7F canonical replay scene in memory. Review it, then save explicitly; canonical replay artifacts were only read at runtime.");
    }

    static M7FFlyRig BuildFly(Transform parent, string name)
    {
        var root = Child(parent, name); var builder = root.gameObject.AddComponent<M7FScientificFlyBuilder>(); builder.Rebuild();
        root.gameObject.AddComponent<M7FAnatomyPresentation>().Rebuild(); return root.GetComponent<M7FFlyRig>();
    }
    static Transform Child(Transform parent, string name) { var value = new GameObject(name).transform; value.SetParent(parent, false); return value; }
    static void AddLabel(Transform parent, string text, Vector3 position) { var value = Child(parent, text); value.localPosition = position; var mesh = value.gameObject.AddComponent<TextMesh>(); mesh.text = text; mesh.anchor = TextAnchor.MiddleCenter; mesh.characterSize = .08f; mesh.fontSize = 42; }
}
