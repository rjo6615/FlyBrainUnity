using System;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;
using FlyBrain.M7FReplay;

namespace FlyBrain.LiveFly
{
    public enum LiveFlyConnectionStatus { Disconnected, Connecting, Connected, Receiving, ProtocolError }

    /// <summary>Output-only TCP viewer. The worker only creates CLR data; Update alone touches the rig.</summary>
    public sealed class LiveFlyClient : MonoBehaviour
    {
        [SerializeField] string host = "127.0.0.1";
        [SerializeField] int port = 8765;
        [SerializeField] bool connectOnStart = true;
        [SerializeField] bool retryConnection = true;
        [SerializeField, Min(.25f)] float retrySeconds = 2f;
        [SerializeField] bool presentationInterpolation;
        [SerializeField] M7FFlyRig rig;
        [Header("Runtime diagnostics (read only)")]
        [SerializeField] LiveFlyConnectionStatus status = LiveFlyConnectionStatus.Disconnected;
        [SerializeField] string sessionId = "";
        [SerializeField] string statusDetail = "";
        [SerializeField] long latestSequence = -1;
        [SerializeField] double latestSimTime;
        [SerializeField] long posesReceived, posesDroppedOrReplaced;

        readonly NewestPoseSlot slot = new NewestPoseSlot();
        readonly object stateGate = new object();
        CancellationTokenSource cancellation; Task worker; TcpClient activeClient;
        WorkerState workerState = new WorkerState(); LiveFlyPose previous, current; float receivedAt;
        sealed class WorkerState { public LiveFlyConnectionStatus Status; public string Session="", Detail=""; public long Received; }

        public LiveFlyConnectionStatus Status => status; public string SessionId => sessionId;
        public long LatestSequence => latestSequence; public double LatestSimTime => latestSimTime;
        public long PosesReceived => posesReceived; public long PosesDroppedOrReplaced => posesDroppedOrReplaced;
        public string Host => host; public int Port => port; public bool ConnectOnStart => connectOnStart;
        public bool PresentationInterpolation => presentationInterpolation; public M7FFlyRig Rig => rig;
        public void Configure(M7FFlyRig targetRig, string targetHost = "127.0.0.1", int targetPort = 8765)
        { rig=targetRig;host=targetHost;port=targetPort;connectOnStart=true;presentationInterpolation=false; }

        void Start() { if (connectOnStart) Connect(); }
        public void Connect()
        {
            if (worker != null && !worker.IsCompleted) return;
            if (rig == null) { status=LiveFlyConnectionStatus.ProtocolError; statusDetail="M7FFlyRig reference is required."; return; }
            if (!rig.ValidateMapping(M7FScientificFlyRigDefinition.Names)) { status=LiveFlyConnectionStatus.ProtocolError; statusDetail=rig.ValidationStatus; return; }
            var expectedJointNames = (string[])M7FScientificFlyRigDefinition.CanonicalNames.Clone();
            cancellation = new CancellationTokenSource(); worker = Task.Run(() => Run(cancellation.Token, host, port, retryConnection, retrySeconds, expectedJointNames));
        }
        public void Disconnect()
        {
            cancellation?.Cancel(); lock(stateGate) activeClient?.Close(); slot.Clear();
            cancellation?.Dispose(); cancellation=null; worker=null; activeClient=null;
            status=LiveFlyConnectionStatus.Disconnected;
        }
        void OnDisable()=>Disconnect(); void OnDestroy()=>Disconnect(); void OnApplicationQuit()=>Disconnect();

        void Update()
        {
            lock(stateGate){status=workerState.Status;sessionId=workerState.Session;statusDetail=workerState.Detail;posesReceived=workerState.Received;}
            posesDroppedOrReplaced=slot.ReplacedCount;
            if(slot.TryTake(out var pose)){previous=current;current=pose;receivedAt=Time.unscaledTime;latestSequence=pose.Sequence;latestSimTime=pose.SimTimeSeconds;}
            if(current==null)return;
            if(!presentationInterpolation||previous==null){Apply(current);return;}
            var t=Mathf.Clamp01((Time.unscaledTime-receivedAt)*30f);
            var p=Vector3.Lerp(LiveFlyCoordinates.PositionMmToUnity(previous.RootPosition),LiveFlyCoordinates.PositionMmToUnity(current.RootPosition),t);
            var q=Quaternion.Slerp(LiveFlyCoordinates.QuaternionWxyzToUnity(previous.RootQuaternionWxyz),LiveFlyCoordinates.QuaternionWxyzToUnity(current.RootQuaternionWxyz),t);
            var joints=new double[LiveFlyProtocol.JointCount];for(var i=0;i<joints.Length;i++)joints[i]=previous.JointPositions[i]+(current.JointPositions[i]-previous.JointPositions[i])*t;
            rig.ApplyLivePose(p,q,joints);
        }
        void Apply(LiveFlyPose pose)=>rig.ApplyLivePose(LiveFlyCoordinates.PositionMmToUnity(pose.RootPosition),LiveFlyCoordinates.QuaternionWxyzToUnity(pose.RootQuaternionWxyz),pose.JointPositions);

        async Task Run(CancellationToken token, string targetHost, int targetPort, bool shouldRetry, float retryDelay, string[] jointNames)
        {
            while(!token.IsCancellationRequested)
            {
                Set(LiveFlyConnectionStatus.Connecting,"Connecting to "+targetHost+":"+targetPort);
                try
                {
                    var client=new TcpClient(); lock(stateGate)activeClient=client;
                    await client.ConnectAsync(targetHost,targetPort);
                    token.ThrowIfCancellationRequested(); Set(LiveFlyConnectionStatus.Connected,"Awaiting hello");
                    using(client) using(var stream=client.GetStream()) using(var reader=new StreamReader(stream,new UTF8Encoding(false,true),false,4096))
                    {
                        var line=await ReadLine(reader,token); if(line==null)throw new IOException("Connection closed before hello.");
                        var hello=LiveFlyProtocol.ParseHello(line,jointNames); Set(LiveFlyConnectionStatus.Receiving,"Receiving authoritative poses",hello.SessionId);
                        while(!token.IsCancellationRequested)
                        {
                            line=await ReadLine(reader,token);if(line==null)throw new IOException("Connection closed.");
                            var pose=LiveFlyProtocol.ParsePose(line,hello.SessionId);slot.Publish(pose);Received();
                        }
                    }
                }
                catch(OperationCanceledException)when(token.IsCancellationRequested){break;}
                catch(LiveFlyProtocolException e){Set(LiveFlyConnectionStatus.ProtocolError,e.Message);}
                catch(Exception e){if(!token.IsCancellationRequested)Set(LiveFlyConnectionStatus.Disconnected,e.Message);}
                finally{lock(stateGate){activeClient?.Close();activeClient=null;}}
                if(!shouldRetry||token.IsCancellationRequested)break;
                try{await Task.Delay(TimeSpan.FromSeconds(Math.Max(.25,retryDelay)),token);}catch(OperationCanceledException){break;}
            }
            if(!token.IsCancellationRequested)Set(LiveFlyConnectionStatus.Disconnected,"Disconnected");
        }
        static async Task<string> ReadLine(StreamReader reader,CancellationToken token){var read=reader.ReadLineAsync();var cancelled=Task.Delay(Timeout.Infinite,token);await Task.WhenAny(read,cancelled);token.ThrowIfCancellationRequested();return await read;}
        void Set(LiveFlyConnectionStatus value,string detail,string session=null){lock(stateGate){workerState.Status=value;workerState.Detail=detail;if(session!=null)workerState.Session=session;}}
        void Received(){lock(stateGate)workerState.Received++;}
    }
}
