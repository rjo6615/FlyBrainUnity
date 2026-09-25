using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace FlyBrain.LiveFly
{
    public sealed class LiveFlyProtocolException : Exception
    {
        public LiveFlyProtocolException(string message) : base(message) { }
        public LiveFlyProtocolException(string message, Exception inner) : base(message, inner) { }
    }

    public sealed class LiveFlyHello
    {
        public string SessionId { get; internal set; }
        public string[] JointNames { get; internal set; }
    }

    public sealed class LiveFlyPose
    {
        public string SessionId { get; internal set; }
        public long Sequence { get; internal set; }
        public double SimTimeSeconds { get; internal set; }
        public double[] RootPosition { get; internal set; }
        public double[] RootQuaternionWxyz { get; internal set; }
        public double[] JointPositions { get; internal set; }
    }

    /// <summary>Pure CLR Live Fly v1 decoder.  It deliberately has no UnityEngine dependency,
    /// so it is safe to execute on the receive thread.</summary>
    public static class LiveFlyProtocol
    {
        public const string Protocol = "live_fly_pose";
        public const int Version = 1;
        public const int JointCount = 42;

        public static LiveFlyHello ParseHello(string json, IReadOnlyList<string> expectedNames)
        {
            var value = Object(json);
            Common(value, "hello");
            if (Integer(value, "joint_count") != JointCount) Fail("hello joint_count must be 42");
            if (String(value, "root_quaternion_order") != "wxyz") Fail("hello quaternion order must be wxyz");
            var names = Strings(value, "joint_names", JointCount);
            if (expectedNames == null || expectedNames.Count != JointCount) Fail("expected M7F joint order is incomplete");
            for (var i = 0; i < JointCount; i++) if (names[i] != expectedNames[i]) Fail("hello joint order differs at index " + i);
            return new LiveFlyHello { SessionId = Session(value), JointNames = names };
        }

        public static LiveFlyPose ParsePose(string json, string helloSessionId)
        {
            var value = Object(json);
            Common(value, "pose");
            var session = Session(value);
            if (string.IsNullOrEmpty(helloSessionId) || session != helloSessionId) Fail("pose session_id does not match hello");
            var sequence = Integer(value, "sequence");
            if (sequence < 0) Fail("sequence must be nonnegative");
            return new LiveFlyPose {
                SessionId = session, Sequence = sequence,
                SimTimeSeconds = Number(value, "sim_time_seconds"),
                RootPosition = Numbers(value, "root_position", 3),
                RootQuaternionWxyz = Numbers(value, "root_quaternion_wxyz", 4),
                JointPositions = Numbers(value, "joint_positions", JointCount)
            };
        }

        static Dictionary<string, object> Object(string json)
        {
            try { return new JsonReader(json).ReadObjectDocument(); }
            catch (LiveFlyProtocolException) { throw; }
            catch (Exception e) { throw new LiveFlyProtocolException("malformed JSON", e); }
        }
        static void Common(Dictionary<string, object> o, string type)
        {
            if (String(o, "type") != type || String(o, "protocol") != Protocol || Integer(o, "version") != Version)
                Fail("not a " + Protocol + " v1 " + type + " message");
        }
        static string Session(Dictionary<string, object> o) { var s = String(o, "session_id"); if (s.Length == 0) Fail("session_id is empty"); return s; }
        static string String(Dictionary<string, object> o, string key) { if (!o.TryGetValue(key, out var v) || !(v is string)) Fail(key + " must be a string"); return (string)v; }
        static long Integer(Dictionary<string, object> o, string key) { if (!o.TryGetValue(key, out var v) || !(v is long)) Fail(key + " must be an integer"); return (long)v; }
        static double Number(Dictionary<string, object> o, string key) { if (!o.TryGetValue(key, out var v) || !(v is double) && !(v is long)) Fail(key + " must be numeric"); var n = v is long l ? l : (double)v; if (double.IsNaN(n) || double.IsInfinity(n)) Fail(key + " must be finite"); return n; }
        static double[] Numbers(Dictionary<string, object> o, string key, int count)
        {
            if (!o.TryGetValue(key, out var v) || !(v is List<object>)) Fail(key + " must contain exactly " + count + " values");
            var a = (List<object>)v; if (a.Count != count) Fail(key + " must contain exactly " + count + " values");
            var result = new double[count]; for (var i = 0; i < count; i++) { var one = new Dictionary<string, object> { { key, a[i] } }; result[i] = Number(one, key); } return result;
        }
        static string[] Strings(Dictionary<string, object> o, string key, int count)
        {
            if (!o.TryGetValue(key, out var v) || !(v is List<object>)) Fail(key + " must contain exactly " + count + " values");
            var a = (List<object>)v; if (a.Count != count) Fail(key + " must contain exactly " + count + " values");
            var result = new string[count]; for (var i = 0; i < count; i++) { if (!(a[i] is string)) Fail(key + " entries must be strings"); result[i] = (string)a[i]; } return result;
        }
        static void Fail(string message) { throw new LiveFlyProtocolException(message); }

        // Small strict RFC-8259 reader avoids calling JsonUtility (a Unity API) from the network thread.
        sealed class JsonReader
        {
            readonly string text; int at;
            public JsonReader(string value) { text = value ?? throw new LiveFlyProtocolException("JSON is null"); }
            public Dictionary<string, object> ReadObjectDocument() { Space(); var v = Value() as Dictionary<string, object>; Space(); if (v == null || at != text.Length) Fail("JSON must be one object"); return v; }
            object Value() { Space(); if (at >= text.Length) Fail("unexpected end of JSON"); var c=text[at]; if(c=='{')return Obj(); if(c=='[')return Array(); if(c=='\"')return Str(); if(c=='-'||char.IsDigit(c))return Num(); if(Take("true"))return true; if(Take("false"))return false; if(Take("null"))return null; Fail("invalid JSON value"); return null; }
            Dictionary<string, object> Obj() { var r=new Dictionary<string,object>(); at++; Space(); if(Peek('}')){at++;return r;} while(true){Space(); if(at>=text.Length||text[at]!='\"')Fail("object key must be a string"); var k=Str(); Space(); Need(':'); if(r.ContainsKey(k))Fail("duplicate object key"); r[k]=Value(); Space(); if(Peek('}')){at++;return r;} Need(',');} }
            List<object> Array() { var r=new List<object>(); at++; Space(); if(Peek(']')){at++;return r;} while(true){r.Add(Value());Space();if(Peek(']')){at++;return r;}Need(',');} }
            string Str() { at++; var b=new StringBuilder(); while(at<text.Length){var c=text[at++];if(c=='\"')return b.ToString();if(c<' ')Fail("control character in string");if(c!='\\'){b.Append(c);continue;}if(at>=text.Length)Fail("bad escape");c=text[at++];if(c=='u'){if(at+4>text.Length)Fail("bad unicode escape");if(!int.TryParse(text.Substring(at,4),NumberStyles.HexNumber,CultureInfo.InvariantCulture,out var code))Fail("bad unicode escape");b.Append((char)code);at+=4;}else{var p="\"\\/bfnrt".IndexOf(c);if(p<0)Fail("bad escape");b.Append("\"\\/\b\f\n\r\t"[p]);}}Fail("unterminated string");return null; }
            object Num() { var start=at;if(Peek('-'))at++;if(at>=text.Length)Fail("bad number");if(Peek('0'))at++;else{if(!char.IsDigit(text[at]))Fail("bad number");while(at<text.Length&&char.IsDigit(text[at]))at++;}var integer=true;if(Peek('.')){integer=false;at++;Digits();}if(Peek('e')||Peek('E')){integer=false;at++;if(Peek('+')||Peek('-'))at++;Digits();}var s=text.Substring(start,at-start);if(integer&&long.TryParse(s,NumberStyles.Integer,CultureInfo.InvariantCulture,out var l))return l;if(double.TryParse(s,NumberStyles.Float,CultureInfo.InvariantCulture,out var d)&&!double.IsInfinity(d)&&!double.IsNaN(d))return d;Fail("bad number");return null; }
            void Digits(){var begin=at;while(at<text.Length&&char.IsDigit(text[at]))at++;if(begin==at)Fail("digits expected");}
            bool Take(string s){if(at+s.Length>text.Length||string.CompareOrdinal(text,at,s,0,s.Length)!=0)return false;at+=s.Length;return true;}
            bool Peek(char c)=>at<text.Length&&text[at]==c; void Need(char c){Space();if(!Peek(c))Fail("expected "+c);at++;} void Space(){while(at<text.Length&&(text[at]==' '||text[at]=='\t'||text[at]=='\r'||text[at]=='\n'))at++;}
        }
    }

    /// <summary>Thread-safe capacity-one mailbox. Publish replaces, rather than queues, stale poses.</summary>
    public sealed class NewestPoseSlot
    {
        readonly object gate = new object(); LiveFlyPose newest; long replacedCount;
        public long ReplacedCount { get { lock(gate) return replacedCount; } }
        public void Publish(LiveFlyPose pose) { if (pose == null) throw new ArgumentNullException(nameof(pose)); lock(gate){if(newest!=null)replacedCount++;newest=pose;} }
        public bool TryTake(out LiveFlyPose pose) { lock(gate){pose=newest;newest=null;return pose!=null;} }
        public void Clear(){lock(gate)newest=null;}
    }
}
