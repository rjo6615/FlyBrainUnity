using System;
using FlyBrain.LiveFly;
using FlyBrain.M7FReplay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class LiveFlySceneGenerator
{
    public const string ScenePath = "Assets/Scenes/LiveFly.unity";

    [MenuItem("FlyBrain/Live Fly/Create Live Fly Scene")]
    public static void CreateLiveFlyScene()
    {
        BuildAndSaveScene();
    }

    /// <summary>Shared, non-GUI construction entry point used by the menu and EditMode validation.</summary>
    public static GameObject BuildAndSaveScene()
    {
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var top = new GameObject("Live Fly — PYTHON/MUJOCO AUTHORITATIVE");

        var fly = Child(top.transform, "FlyRoot — TRANSFORM-ONLY OUTPUT");
        var rig = M7FFlyPresentationBuilder.Build(fly);

        var receiver = Child(top.transform, "Live Fly Client — OUTPUT ONLY");
        receiver.gameObject.AddComponent<LiveFlyClient>().Configure(rig, "127.0.0.1", 8765);

        var environment = Child(top.transform, "Presentation Environment — VISUAL ONLY");
        var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
        ground.name = "Visual Ground — PRESENTATION REFERENCE ONLY";
        ground.transform.SetParent(environment, false);
        ground.transform.localScale = Vector3.one * .08f;
        UnityEngine.Object.DestroyImmediate(ground.GetComponent<Collider>());

        var cameraRig = Child(top.transform, "Camera Rig — PRESENTATION FOLLOW");
        var cameraObject = Child(cameraRig, "Main Camera");
        cameraObject.tag = "MainCamera";
        var camera = cameraObject.gameObject.AddComponent<Camera>();
        camera.nearClipPlane = .001f;
        camera.farClipPlane = 100f;
        cameraObject.gameObject.AddComponent<AudioListener>();
        cameraObject.gameObject.AddComponent<M7FReplayCamera>().Configure(rig.ScientificRoot, M7FScientificFlyBuilder.ApproximateVisualRadius);

        var lighting = Child(top.transform, "Lighting");
        var lightObject = Child(lighting, "Directional Light");
        var light = lightObject.gameObject.AddComponent<Light>();
        light.type = LightType.Directional;
        light.intensity = 1.1f;
        lightObject.rotation = Quaternion.Euler(45f, -35f, 0f);

        Validate(top, rig);
        EditorSceneManager.MarkSceneDirty(scene);
        if (!EditorSceneManager.SaveScene(scene, ScenePath))
            throw new InvalidOperationException("Unity could not save the Live Fly scene at " + ScenePath);
        Selection.activeGameObject = top;
        Debug.Log("Created Live Fly presentation scene. No scientific transition or canonical export was executed.");
        return top;
    }

    public static void Validate(GameObject top, M7FFlyRig expectedRig)
    {
        var rigs = top.GetComponentsInChildren<M7FFlyRig>(true);
        var clients = top.GetComponentsInChildren<LiveFlyClient>(true);
        if (rigs.Length != 1 || rigs[0] != expectedRig) throw new InvalidOperationException("Live Fly scene requires exactly one authoritative M7FFlyRig.");
        if (clients.Length != 1 || clients[0].Rig != expectedRig) throw new InvalidOperationException("Live Fly scene requires exactly one client assigned to its rig.");
        if (!expectedRig.ValidateMapping(M7FScientificFlyRigDefinition.Names)) throw new InvalidOperationException(expectedRig.ValidationStatus);
        if (expectedRig.GetComponentsInChildren<Rigidbody>(true).Length != 0 || expectedRig.GetComponentsInChildren<ArticulationBody>(true).Length != 0 || expectedRig.GetComponentsInChildren<CharacterController>(true).Length != 0 || expectedRig.GetComponentsInChildren<Animator>(true).Length != 0)
            throw new InvalidOperationException("The authoritative Live Fly must remain transform-only.");
    }

    static Transform Child(Transform parent, string name)
    {
        var child = new GameObject(name).transform;
        child.SetParent(parent, false);
        return child;
    }
}
