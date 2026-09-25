using FlyBrain.M7FReplay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

public static class M7FCanonicalReplaySceneGenerator
{
    [MenuItem("Fly Brain/M7F/Create Canonical Replay Scene")]
    public static void CreateCanonicalReplayScene()
    { CreateReplayScene(false); }

    [MenuItem("Fly Brain/M8/Create Extended Spontaneous Replay Scene")]
    public static void CreateM8ReplayScene()
    { CreateReplayScene(true); }

    [MenuItem("Fly Brain/M9D/Create External Perturbation Replay Scene")]
    public static void CreateM9DReplayScene()
    {
        var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single); var top=new GameObject("M9D Canonical M9B Replay"); top.AddComponent<M7FCanonicalReplayPresentation>();
        var system=Child(top.transform,"ReplaySystem"); var loader=system.gameObject.AddComponent<M9DReplayLoader>(); var controller=system.gameObject.AddComponent<M9DReplayController>(); var ui=system.gameObject.AddComponent<M9DScientificUI>();
        var left=BuildFly(top.transform,"A_P — Brain Enabled + Push"); var right=BuildFly(top.transform,"B_P — Brain Disabled + Push"); controller.Configure(loader,left,right); ui.Configure(controller);
        var environment=Child(top.transform,"Environment"); var ground=GameObject.CreatePrimitive(PrimitiveType.Plane); ground.name="VisualGround — PRESENTATION REFERENCE ONLY"; ground.transform.SetParent(environment,false); ground.transform.localScale=Vector3.one*.8f; Object.DestroyImmediate(ground.GetComponent<Collider>());
        var cameraRig=Child(top.transform,"SynchronizedCameraRig"); var cameraObject=Child(cameraRig,"Main Camera"); cameraObject.tag="MainCamera"; var camera=cameraObject.gameObject.AddComponent<Camera>(); camera.nearClipPlane=.01f; camera.farClipPlane=100; cameraObject.gameObject.AddComponent<AudioListener>(); var replayCamera=cameraObject.gameObject.AddComponent<M7FReplayCamera>(); replayCamera.Configure(top.transform,.05f); replayCamera.ConfigureComparison(left,right); ui.Configure(controller,replayCamera);
        var arrow=new GameObject(M9DForceArrow.Annotation); arrow.transform.SetParent(left.transform,false); arrow.AddComponent<M9DForceArrow>().Configure(controller,FindDescendant(left.transform,"Thorax")); AddArrowGeometry(arrow.transform);
        var label=arrow.AddComponent<TextMesh>(); label.text=M9DForceArrow.Annotation+"\n"+M9DForceArrow.Detail; label.characterSize=.014f; label.anchor=TextAnchor.LowerCenter; label.transform.localPosition=new Vector3(0,.04f,.42f);
        var leftTrace=CreateTrace(top.transform,"A_P "+M9DTrajectoryTrace.Annotation,controller,new Color(.2f,.85f,1f)); var rightTrace=CreateTrace(top.transform,"B_P "+M9DTrajectoryTrace.Annotation,controller,new Color(1f,.45f,.15f)); controller.ConfigureTraces(leftTrace,rightTrace);
        var lighting=Child(top.transform,"Lighting"); var lightObject=Child(lighting,"Directional Light"); var light=lightObject.gameObject.AddComponent<Light>(); light.type=LightType.Directional; light.intensity=1.1f; lightObject.rotation=Quaternion.Euler(45,-35,0);
        ValidateM9DConstruction(top, controller, ui);
        EditorSceneManager.MarkSceneDirty(scene); Selection.activeGameObject=top; Debug.Log("Created M9D replay scene in memory. No scientific transition or canonical export was executed.");
    }

    public static void ValidateM9DConstruction(GameObject top, M9DReplayController controller, M9DScientificUI ui)
    {
        if (top == null) throw new System.InvalidOperationException("M9D generated root is null.");
        foreach (var item in top.GetComponentsInChildren<Transform>(true))
            if (GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(item.gameObject) != 0)
                throw new System.InvalidOperationException("M9D generated object contains a missing MonoBehaviour: " + item.name);
        if (controller == null || controller.Loader == null || controller.LeftRig == null || controller.RightRig == null)
            throw new System.InvalidOperationException("M9D controller dependencies were not assigned by the scene generator.");
        if (ui == null || ui.Controller != controller) throw new System.InvalidOperationException("M9D UI does not reference the generated controller.");
        if (controller.LeftRig == controller.RightRig) throw new System.InvalidOperationException("M9D comparison requires two distinct rigs.");
        if (controller.LeftRig.Joints.Count != M7FScientificFlyRigDefinition.JointCount || controller.RightRig.Joints.Count != M7FScientificFlyRigDefinition.JointCount)
            throw new System.InvalidOperationException("M9D generated rigs do not contain both canonical 42-joint mappings.");
        M7FAnatomyPresentation.ValidatePresentation(controller.LeftRig.transform);
        M7FAnatomyPresentation.ValidatePresentation(controller.RightRig.transform);
        if (top.GetComponentsInChildren<Rigidbody>(true).Length != 0 || top.GetComponentsInChildren<Collider>(true).Length != 0)
            throw new System.InvalidOperationException("M9D generated presentation contains forbidden Unity physics authority.");
    }

    static Transform FindDescendant(Transform root,string name) { foreach(var value in root.GetComponentsInChildren<Transform>(true))if(value.name==name)return value; return root; }

    static M9DTrajectoryTrace CreateTrace(Transform parent,string name,M9DReplayController controller,Color color)
    { var trace=Child(parent,name).gameObject; var line=trace.AddComponent<LineRenderer>(); line.sharedMaterial=AssetDatabase.GetBuiltinExtraResource<Material>("Default-Line.mat"); var component=trace.AddComponent<M9DTrajectoryTrace>(); component.Configure(controller,color); return component; }
    static void AddArrowGeometry(Transform parent)
    {
        var shaft=GameObject.CreatePrimitive(PrimitiveType.Cylinder); shaft.name="Presentation-only arrow shaft"; shaft.transform.SetParent(parent,false); shaft.transform.localPosition=Vector3.forward*.2f; shaft.transform.localRotation=Quaternion.Euler(90,0,0); shaft.transform.localScale=new Vector3(.025f,.2f,.025f); Object.DestroyImmediate(shaft.GetComponent<Collider>());
        var head=GameObject.CreatePrimitive(PrimitiveType.Sphere); head.name="Presentation-only arrow head"; head.transform.SetParent(parent,false); head.transform.localPosition=Vector3.forward*.4f; head.transform.localScale=new Vector3(.09f,.09f,.14f); Object.DestroyImmediate(head.GetComponent<Collider>());
        foreach(var renderer in parent.GetComponentsInChildren<Renderer>(true)) renderer.sharedMaterial.color=new Color(1f,.1f,.05f);
    }

    static void CreateReplayScene(bool m8)
    {
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var top = new GameObject(m8 ? "M8 Extended Spontaneous Replay" : "M7F Canonical Replay");
        top.AddComponent<M7FCanonicalReplayPresentation>();
        var replaySystem = Child(top.transform, "ReplaySystem");
        var loader = replaySystem.gameObject.AddComponent<M7FReplayLoader>();
        if (m8) loader.ConfigureM8();
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
        Debug.Log(m8 ? "Created presentation-only M8 replay scene in memory using the validated M7F/VIS3 viewer. Review it, then save explicitly."
            : "Created M7F canonical replay scene in memory. Review it, then save explicitly; canonical replay artifacts were only read at runtime.");
    }

    static M7FFlyRig BuildFly(Transform parent, string name)
    {
        return M7FFlyPresentationBuilder.Build(Child(parent, name));
    }
    static Transform Child(Transform parent, string name) { var value = new GameObject(name).transform; value.SetParent(parent, false); return value; }
    static void AddLabel(Transform parent, string text, Vector3 position) { var value = Child(parent, text); value.localPosition = position; var mesh = value.gameObject.AddComponent<TextMesh>(); mesh.text = text; mesh.anchor = TextAnchor.MiddleCenter; mesh.characterSize = .08f; mesh.fontSize = 42; }
}
