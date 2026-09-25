using System;
using UnityEngine;
using FlyBrain.M7FReplay;

namespace FlyBrain.LiveFly
{
    /// <summary>The single Live Fly source-to-M7F presentation conversion boundary.</summary>
    public static class LiveFlyCoordinates
    {
        public static Vector3 PositionMmToUnity(double[] xyz)
        {
            Require(xyz, 3, "position");
            return M7FCoordinates.SourcePositionToUnity(new Vector3((float)xyz[0], (float)xyz[1], (float)xyz[2])) * M7FCoordinates.MillimetresToUnity;
        }

        public static Quaternion QuaternionWxyzToUnity(double[] wxyz)
        {
            Require(wxyz, 4, "quaternion");
            // B maps polar vectors [x,y,z] -> [x,z,y], det(B)=-1.  Orientation is
            // R_u = B R_s B^-1, not a component reorder. M7FCoordinates realizes
            // that conjugation by mapping rotated source forward/up vectors.
            return M7FCoordinates.SourceQuaternionToUnity(new Quaternion((float)wxyz[1], (float)wxyz[2], (float)wxyz[3], (float)wxyz[0]));
        }
        static void Require(double[] value,int count,string name){if(value==null||value.Length!=count)throw new ArgumentException(name+" has the wrong length");for(var i=0;i<count;i++)if(double.IsNaN(value[i])||double.IsInfinity(value[i]))throw new ArgumentException(name+" must be finite");}
    }
}
