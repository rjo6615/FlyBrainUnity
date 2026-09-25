using UnityEngine;

namespace FlyBrain.M7FReplay
{
    /// <summary>The shared validated M7F/VIS3 transform-rig and anatomy presentation path.</summary>
    public static class M7FFlyPresentationBuilder
    {
        public static M7FFlyRig Build(Transform root)
        {
            root.gameObject.AddComponent<M7FScientificFlyBuilder>().Rebuild();
            root.gameObject.AddComponent<M7FAnatomyPresentation>().Rebuild();
            return root.GetComponent<M7FFlyRig>();
        }
    }
}
