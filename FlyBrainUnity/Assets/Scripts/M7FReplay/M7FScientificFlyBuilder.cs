using System.Collections.Generic;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    /// <summary>Creates presentation geometry and transform-only scientific hinges. It never steps a simulation.</summary>
    public sealed class M7FScientificFlyBuilder : MonoBehaviour
    {
        [SerializeField] bool showJointMarkers = true;
        public const float ApproximateVisualRadius = .03f;

        [ContextMenu("BUILD SCIENTIFIC FLY (NO PHYSICS)")]
        public void Rebuild()
        {
            for (var i = transform.childCount - 1; i >= 0; i--) SafeDestroy(transform.GetChild(i).gameObject);
            var scientificRoot = Child(transform, "ScientificRoot");
            var anatomy = Child(scientificRoot, "PresentationAnatomy");
            var bodyMaterial = Material("M7F neutral body", new Color(.11f, .10f, .09f));
            var legMaterial = Material("M7F segmented legs", new Color(.20f, .17f, .13f));
            var eyeMaterial = Material("M7F eyes (presentation)", new Color(.32f, .08f, .06f));
            var wingMaterial = Material("M7F translucent wings", new Color(.65f, .72f, .76f, .42f));
            wingMaterial.SetFloat("_Mode", 3); wingMaterial.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha); wingMaterial.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha); wingMaterial.SetInt("_ZWrite", 0); wingMaterial.EnableKeyword("_ALPHABLEND_ON"); wingMaterial.renderQueue = 3000;

            Primitive(anatomy, "ThoraxVisual", PrimitiveType.Sphere, new Vector3(0, .004f, 0), new Vector3(.012f, .010f, .009f), bodyMaterial);
            Primitive(anatomy, "AbdomenVisual", PrimitiveType.Sphere, new Vector3(-.011f, .004f, 0), new Vector3(.017f, .007f, .007f), bodyMaterial);
            Primitive(anatomy, "HeadVisual", PrimitiveType.Sphere, new Vector3(.010f, .004f, 0), Vector3.one * .008f, bodyMaterial);
            Primitive(anatomy, "LeftEyeVisual", PrimitiveType.Sphere, new Vector3(.012f, .005f, .004f), new Vector3(.005f, .005f, .003f), eyeMaterial);
            Primitive(anatomy, "RightEyeVisual", PrimitiveType.Sphere, new Vector3(.012f, .005f, -.004f), new Vector3(.005f, .005f, .003f), eyeMaterial);
            var leftWing = Primitive(anatomy, "LeftWingVisual", PrimitiveType.Sphere, new Vector3(-.002f, .008f, .008f), new Vector3(.018f, .001f, .008f), wingMaterial); leftWing.localRotation = Quaternion.Euler(0, -22, 0);
            var rightWing = Primitive(anatomy, "RightWingVisual", PrimitiveType.Sphere, new Vector3(-.002f, .008f, -.008f), new Vector3(.018f, .001f, .008f), wingMaterial); rightWing.localRotation = Quaternion.Euler(0, 22, 0);

            foreach (var leg in M7FScientificFlyRigDefinition.Legs) BuildLeg(scientificRoot, leg, legMaterial);
            var rig = GetComponent<M7FFlyRig>() ?? gameObject.AddComponent<M7FFlyRig>();
            rig.Configure(scientificRoot, System.Array.Empty<M7FJointBinding>()); rig.AutoBindCanonicalJoints();
        }

        void BuildLeg(Transform root, string leg, Material material)
        {
            var left = leg[0] == 'L'; var rank = leg[1] == 'F' ? 0 : leg[1] == 'M' ? 1 : 2;
            var legRoot = Child(root, leg + "_LegRoot"); legRoot.localPosition = M7FScientificFlyRigDefinition.BodyReferencePosition(leg, 0);
            // Coincident hinge nesting follows MJCF element order, not manifest array order.
            Transform pivot = legRoot; var transforms = new Dictionary<string, Transform>();
            foreach (var name in M7FScientificFlyRigDefinition.HierarchyOrder(leg))
            {
                pivot = Child(pivot, name); transforms[name] = pivot;
                if (name.EndsWith("Femur_roll")) pivot.localPosition = M7FScientificFlyRigDefinition.BodyReferencePosition(leg, 1);
                else if (name.EndsWith("Tibia")) pivot.localPosition = M7FScientificFlyRigDefinition.BodyReferencePosition(leg, 2);
                else if (name.EndsWith("Tarsus1")) pivot.localPosition = M7FScientificFlyRigDefinition.BodyReferencePosition(leg, 3);
                if (showJointMarkers) Primitive(pivot, name + "_JointMarker", PrimitiveType.Sphere, Vector3.zero, Vector3.one * .0012f, material);
            }
            transforms["joint_" + leg + "Coxa_roll"].localRotation = M7FScientificFlyRigDefinition.BodyReferenceRotation(leg, 0);
            transforms["joint_" + leg + "Femur_roll"].localRotation *= M7FScientificFlyRigDefinition.BodyReferenceRotation(leg, 1);
            transforms["joint_" + leg + "Tibia"].localRotation *= M7FScientificFlyRigDefinition.BodyReferenceRotation(leg, 2);
            transforms["joint_" + leg + "Tarsus1"].localRotation *= M7FScientificFlyRigDefinition.BodyReferenceRotation(leg, 3);
            var outward = left ? 1f : -1f;
            AddSegment(transforms["joint_" + leg + "Coxa"], leg + "_CoxaVisual", Vector3.zero, .005f, outward, material);
            AddSegment(transforms["joint_" + leg + "Femur"], leg + "_FemurVisual", Vector3.zero, .008f, outward, material);
            AddSegment(transforms["joint_" + leg + "Tibia"], leg + "_TibiaVisual", Vector3.zero, .010f, outward, material);
            AddSegment(transforms["joint_" + leg + "Tarsus1"], leg + "_TarsusVisual", Vector3.zero, .007f, outward, material);
        }

        static void AddSegment(Transform parent, string name, Vector3 endpoint, float length, float side, Material material)
        {
            var visual = Primitive(parent, name, PrimitiveType.Cylinder, new Vector3(0, -length * .5f, side * length * .14f), new Vector3(.001f, length * .5f, .001f), material);
            visual.localRotation = Quaternion.Euler(side * 18f, 0, endpoint.x * 30f);
            var continuation = Child(parent, name + "_DistalReference"); continuation.localPosition = endpoint;
        }

        static Transform Child(Transform parent, string name) { var value = new GameObject(name).transform; value.SetParent(parent, false); return value; }
        static Transform Primitive(Transform parent, string name, PrimitiveType type, Vector3 position, Vector3 scale, Material material)
        {
            var value = GameObject.CreatePrimitive(type); value.name = name; value.transform.SetParent(parent, false); value.transform.localPosition = position; value.transform.localScale = scale;
            var collider = value.GetComponent<Collider>(); if (collider != null) SafeDestroy(collider);
            value.GetComponent<Renderer>().sharedMaterial = material; return value.transform;
        }
        static Material Material(string name, Color color) { var shader = Shader.Find("Standard") ?? Shader.Find("Universal Render Pipeline/Lit"); var result = new Material(shader) { name = name, color = color }; return result; }
        static void SafeDestroy(Object value) { if (Application.isPlaying) Object.Destroy(value); else Object.DestroyImmediate(value); }
    }
}
