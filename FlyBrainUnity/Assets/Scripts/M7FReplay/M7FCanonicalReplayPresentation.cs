using UnityEngine;

namespace FlyBrain.M7FReplay
{
    /// <summary>
    /// Marks the canonical replay as a clean VIS3 presentation. The optional legacy bridge
    /// presentation contains its own decorative fly and RGB origin axes; it never contributes
    /// scientific transforms or authoritative anatomy.
    /// </summary>
    public sealed class M7FCanonicalReplayPresentation : MonoBehaviour
    {
        [SerializeField, Tooltip("Debug only: also show UnityFlyBridge's legacy fly and RGB world axes.")]
        bool showLegacyBridgeDebugPresentation;

        public bool ShowLegacyBridgeDebugPresentation => showLegacyBridgeDebugPresentation;

        public static bool AllowsLegacyBridgePresentationInCurrentScene()
        {
            var canonical = FindFirstObjectByType<M7FCanonicalReplayPresentation>();
            return canonical == null || canonical.showLegacyBridgeDebugPresentation;
        }
    }
}
