Shader "Fly Brain/Brown Mud Leaves Anti-Tile"
{
    Properties
    {
        [MainTexture] _BaseMap("Base Color", 2D) = "white" {}
        [Normal] _BumpMap("Normal Map", 2D) = "bump" {}
        _MetallicGlossMap("Metallic (R) Smoothness (A)", 2D) = "white" {}
        _OcclusionMap("Occlusion (G)", 2D) = "white" {}
        [MainColor] _BaseColor("Tint", Color) = (1,1,1,1)
        _PrimaryTiling("Primary Tiling", Range(1,64)) = 16
        _SecondaryScale("Secondary UV Scale", Range(0.5,1.5)) = 0.83
        _MacroVariationStrength("Macro Variation Strength", Range(0,0.07)) = 0.03
        _MacroVariationScale("Macro Variation Scale", Range(0.25,8)) = 1.35
        [Enum(Base Color Only,0,Standard PBR,1,PBR + Anti-Tiling,2,PBR + Anti-Tiling + Macro Variation,3)]
        _GroundRenderingMode("Ground Rendering Mode", Float) = 3
        _BumpScale("Normal Strength", Range(0,2)) = 1
        _Smoothness("Smoothness", Range(0,1)) = 1
        _OcclusionStrength("Occlusion Strength", Range(0,1)) = 1
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" "RenderPipeline"="UniversalPipeline" }
        LOD 300

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile _ _FORWARD_PLUS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
            TEXTURE2D(_BumpMap); SAMPLER(sampler_BumpMap);
            TEXTURE2D(_MetallicGlossMap); SAMPLER(sampler_MetallicGlossMap);
            TEXTURE2D(_OcclusionMap); SAMPLER(sampler_OcclusionMap);

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseColor;
                float _PrimaryTiling, _SecondaryScale, _MacroVariationStrength, _MacroVariationScale;
                float _GroundRenderingMode;
                float _BumpScale, _Smoothness, _OcclusionStrength;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float4 tangentOS : TANGENT; float2 uv : TEXCOORD0; };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                half3 normalWS : TEXCOORD1;
                half4 tangentWS : TEXCOORD2;
                float2 uv : TEXCOORD3;
                half fogFactor : TEXCOORD4;
            };

            float Hash(float2 p) { return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453); }
            float ValueNoise(float2 p)
            {
                float2 i = floor(p), f = frac(p); f = f * f * (3.0 - 2.0 * f);
                return lerp(lerp(Hash(i), Hash(i + float2(1,0)), f.x),
                            lerp(Hash(i + float2(0,1)), Hash(i + 1.0), f.x), f.y);
            }

            Varyings Vert(Attributes input)
            {
                Varyings output;
                VertexPositionInputs pos = GetVertexPositionInputs(input.positionOS.xyz);
                VertexNormalInputs nrm = GetVertexNormalInputs(input.normalOS, input.tangentOS);
                output.positionCS = pos.positionCS; output.positionWS = pos.positionWS;
                output.normalWS = nrm.normalWS;
                output.tangentWS = half4(nrm.tangentWS, input.tangentOS.w * GetOddNegativeScale());
                output.uv = input.uv; output.fogFactor = ComputeFogFactor(pos.positionCS.z);
                return output;
            }

            half4 Frag(Varyings input) : SV_Target
            {
                float2 uv1 = input.uv * _PrimaryTiling;
                // Non-integer frequency, quarter-turn, and offset decorrelate recognizable leaves.
                float2 uv2 = float2(-input.uv.y, input.uv.x) * (_PrimaryTiling * _SecondaryScale) + float2(0.37, 0.61);
                float macro = ValueNoise(input.uv * _MacroVariationScale + float2(2.1, 5.7));
                // Noise selects between two valid texture samples. It never darkens either sample.
                float blend = smoothstep(0.30, 0.70, macro);
                bool antiTiling = _GroundRenderingMode >= 1.5;
                blend = antiTiling ? blend : 0.0;

                half3 base1 = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, uv1).rgb;
                half3 base2 = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, uv2).rgb;
                half3 albedo = lerp(base1, base2, blend) * _BaseColor.rgb;
                // At the default strength this is a brightness-only 0.97--1.03 multiplier.
                // Strength zero is an exact no-op, preserving the normal PBR appearance.
                if (_GroundRenderingMode >= 2.5)
                    albedo *= lerp(1.0h - (half)_MacroVariationStrength,
                                   1.0h + (half)_MacroVariationStrength, (half)macro);

                // Mode zero deliberately bypasses lighting and all PBR maps. This is the imported,
                // sRGB-decoded base color (plus the white material tint) for diagnosis.
                if (_GroundRenderingMode < 0.5)
                    return half4(albedo, 1.0h);

                half3 normal1 = UnpackNormalScale(SAMPLE_TEXTURE2D(_BumpMap, sampler_BumpMap, uv1), _BumpScale);
                half3 normal2 = UnpackNormalScale(SAMPLE_TEXTURE2D(_BumpMap, sampler_BumpMap, uv2), _BumpScale);
                normal2.xy = half2(normal2.y, -normal2.x);
                half3 normalTS = normalize(lerp(normal1, normal2, blend));
                half3 bitangent = input.tangentWS.w * cross(input.normalWS, input.tangentWS.xyz);
                half3 normalWS = normalize(TransformTangentToWorld(normalTS,
                    half3x3(input.tangentWS.xyz, bitangent, input.normalWS)));

                half4 mask1 = SAMPLE_TEXTURE2D(_MetallicGlossMap, sampler_MetallicGlossMap, uv1);
                half4 mask2 = SAMPLE_TEXTURE2D(_MetallicGlossMap, sampler_MetallicGlossMap, uv2);
                half smoothness = lerp(mask1.a, mask2.a, blend) * _Smoothness;
                half ao1 = SAMPLE_TEXTURE2D(_OcclusionMap, sampler_OcclusionMap, uv1).g;
                half ao2 = SAMPLE_TEXTURE2D(_OcclusionMap, sampler_OcclusionMap, uv2).g;
                // Occlusion is supplied only to URP lighting; it is never multiplied into albedo.
                half occlusion = lerp(1.0h, lerp(ao1, ao2, blend), _OcclusionStrength);

                InputData data = (InputData)0;
                data.positionWS = input.positionWS; data.normalWS = normalWS;
                data.viewDirectionWS = GetWorldSpaceNormalizeViewDir(input.positionWS);
                data.shadowCoord = TransformWorldToShadowCoord(input.positionWS);
                data.fogCoord = input.fogFactor;
                data.bakedGI = SampleSH(normalWS);
                data.vertexLighting = VertexLighting(input.positionWS, normalWS);
                data.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(input.positionCS);
                data.shadowMask = half4(1, 1, 1, 1);
                SurfaceData surface = (SurfaceData)0;
                surface.albedo = albedo; surface.alpha = 1; surface.metallic = 0;
                surface.specular = 0; surface.smoothness = smoothness;
                surface.normalTS = normalTS; surface.occlusion = occlusion;
                half4 color = UniversalFragmentPBR(data, surface);
                color.rgb = MixFog(color.rgb, input.fogFactor);
                return color;
            }
            ENDHLSL
        }
        UsePass "Universal Render Pipeline/Lit/ShadowCaster"
        UsePass "Universal Render Pipeline/Lit/DepthOnly"
        UsePass "Universal Render Pipeline/Lit/DepthNormals"
        UsePass "Universal Render Pipeline/Lit/Meta"
    }
    FallBack "Hidden/Universal Render Pipeline/FallbackError"
}
