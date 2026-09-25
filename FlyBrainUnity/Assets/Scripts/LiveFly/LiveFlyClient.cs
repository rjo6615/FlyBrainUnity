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
    public enum LiveFlyConnectionStatus { Disconnected, Connecting, AwaitingHello, AwaitingFirstPose, Receiving, ErrorRetrying, Error }

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
        [SerializeField] bool tcpConnected, helloReceived, helloAccepted;
        [SerializeField] long rawLinesReceived, poseLinesReceived, posesAccepted, posesRejected;
        [SerializeField] long posesConsumedByUpdate, posesAppliedToRig, posesDroppedOrReplaced;
        [SerializeField] string lastProtocolParserOrTransportError = "";

        readonly NewestPoseSlot slot = new NewestPoseSlot();
        readonly object stateGate = new object();
        CancellationTokenSource cancellation; Task worker; TcpClient activeClient;
        WorkerState workerState = new WorkerState(); LiveFlyPose previous, current; float receivedAt; long lastAppliedSequence=-1;
        readonly System.Collections.Concurrent.ConcurrentQueue<string> consoleErrors = new System.Collections.Concurrent.ConcurrentQueue<string>();
        sealed class WorkerState
        {
            public LiveFlyConnectionStatus Status; public string Session="", Detail="", LastError="";
            public bool TcpConnected, HelloReceived, HelloAccepted;
            public long RawLines, PoseLines, Accepted, Rejected, LatestSequence=-1;
            public double LatestSimTime;
        }

        public LiveFlyConnectionStatus Status => status; public string SessionId => sessionId;
        public long LatestSequence => latestSequence; public double LatestSimTime => latestSimTime;
        public long PosesReceived => posesAccepted; public long PosesDroppedOrReplaced => posesDroppedOrReplaced;
        public bool TcpConnected => tcpConnected; public bool HelloReceived => helloReceived; public bool HelloAccepted => helloAccepted;
        public long RawLinesReceived => rawLinesReceived; public long PoseLinesReceived => poseLinesReceived;
        public long PosesAccepted => posesAccepted; public long PosesRejected => posesRejected;
        public long PosesConsumedByUpdate => posesConsumedByUpdate; public long PosesAppliedToRig => posesAppliedToRig;
        public string LastProtocolParserOrTransportError => lastProtocolParserOrTransportError;
        public string Host => host; public int Port => port; public bool ConnectOnStart => connectOnStart;
        public bool PresentationInterpolation => presentationInterpolation; public M7FFlyRig Rig => rig;
        public void Configure(M7FFlyRig targetRig, string targetHost = "127.0.0.1", int targetPort = 8765)
        { rig=targetRig;host=targetHost;port=targetPort;connectOnStart=true;presentationInterpolation=false; }

        void Start() { if (connectOnStart) Connect(); }
        public void Connect()
        {
            if (worker != null && !worker.IsCompleted) return;
            if (rig == null) { status=LiveFlyConnectionStatus.Error; statusDetail="M7FFlyRig reference is required."; return; }
            if (!rig.ValidateMapping(M7FScientificFlyRigDefinition.Names)) { status=LiveFlyConnectionStatus.Error; statusDetail=rig.ValidationStatus; return; }
            var expectedJointNames = (string[])M7FScientificFlyRigDefinition.CanonicalNames.Clone();
            cancellation = new CancellationTokenSource(); worker = Task.Run(() => Run(cancellation.Token, host, port, retryConnection, retrySeconds, expectedJointNames));
        }
        public void Disconnect()
        {
            cancellation?.Cancel(); lock(stateGate) activeClient?.Close(); slot.Clear();
            cancellation?.Dispose(); cancellation=null; worker=null; activeClient=null;
            lock(stateGate){workerState.Status=LiveFlyConnectionStatus.Disconnected;workerState.Detail="Disconnected";workerState.TcpConnected=false;}
            status=LiveFlyConnectionStatus.Disconnected; tcpConnected=false;
        }
        void OnDisable()=>Disconnect(); void OnDestroy()=>Disconnect(); void OnApplicationQuit()=>Disconnect();

        void Update()
        {
            lock(stateGate)
            {
                status=workerState.Status; sessionId=workerState.Session; statusDetail=workerState.Detail;
                tcpConnected=workerState.TcpConnected; helloReceived=workerState.HelloReceived; helloAccepted=workerState.HelloAccepted;
                rawLinesReceived=workerState.RawLines; poseLinesReceived=workerState.PoseLines;
                posesAccepted=workerState.Accepted; posesRejected=workerState.Rejected;
                latestSequence=workerState.LatestSequence; latestSimTime=workerState.LatestSimTime;
                lastProtocolParserOrTransportError=workerState.LastError;
            }
            while(consoleErrors.TryDequeue(out var error)) Debug.LogError("[Live Fly] "+error,this);
            posesDroppedOrReplaced=slot.ReplacedCount;
            if(slot.TryTake(out var pose)){previous=current;current=pose;receivedAt=Time.unscaledTime;posesConsumedByUpdate++;}
            if(current==null)return;
            if(!presentationInterpolation||previous==null){Apply(current);MarkApplied(current);return;}
            var t=Mathf.Clamp01((Time.unscaledTime-receivedAt)*30f);
            var p=Vector3.Lerp(LiveFlyCoordinates.PositionMmToUnity(previous.RootPosition),LiveFlyCoordinates.PositionMmToUnity(current.RootPosition),t);
            var q=Quaternion.Slerp(LiveFlyCoordinates.QuaternionWxyzToUnity(previous.RootQuaternionWxyz),LiveFlyCoordinates.QuaternionWxyzToUnity(current.RootQuaternionWxyz),t);
            var joints=new double[LiveFlyProtocol.JointCount];for(var i=0;i<joints.Length;i++)joints[i]=previous.JointPositions[i]+(current.JointPositions[i]-previous.JointPositions[i])*t;
            rig.ApplyLivePose(p,q,joints);
            MarkApplied(current);
        }
        void Apply(LiveFlyPose pose)=>rig.ApplyLivePose(LiveFlyCoordinates.PositionMmToUnity(pose.RootPosition),LiveFlyCoordinates.QuaternionWxyzToUnity(pose.RootQuaternionWxyz),pose.JointPositions);
        void MarkApplied(LiveFlyPose pose){if(lastAppliedSequence==pose.Sequence)return;lastAppliedSequence=pose.Sequence;posesAppliedToRig++;}

        async Task Run(CancellationToken token, string targetHost, int targetPort, bool shouldRetry, float retryDelay, string[] jointNames)
        {
            while(!token.IsCancellationRequested)
            {
                Set(LiveFlyConnectionStatus.Connecting,"Connecting to "+targetHost+":"+targetPort);
                try
                {
                    var client=new TcpClient(); lock(stateGate)activeClient=client;
                    await client.ConnectAsync(targetHost,targetPort);
                    token.ThrowIfCancellationRequested(); Connected(); Set(LiveFlyConnectionStatus.AwaitingHello,"TCP connected / Awaiting Hello");
                    using(client) using(var stream=client.GetStream()) using(var reader=new StreamReader(stream,new UTF8Encoding(false,true),false,4096))
                    {
                        var line=await ReadLine(reader,token); if(line==null)throw new IOException("Connection closed before hello.");
                        LineReceived(true); var hello=LiveFlyProtocol.ParseHello(line,jointNames); HelloAccepted();
                        Set(LiveFlyConnectionStatus.AwaitingFirstPose,"Hello accepted; awaiting first authoritative pose",hello.SessionId);
                        while(!token.IsCancellationRequested)
                        {
                            line=await ReadLine(reader,token);if(line==null)throw new IOException("Connection closed.");
                            LineReceived(false);
                            LiveFlyPose pose;
                            try { pose=LiveFlyProtocol.ParsePose(line,hello.SessionId); }
                            catch(LiveFlyProtocolException) { Rejected(); throw; }
                            slot.Publish(pose); Accepted(pose);
                            Set(LiveFlyConnectionStatus.Receiving,"Receiving authoritative poses",hello.SessionId);
                        }
                    }
                }
                catch(OperationCanceledException)when(token.IsCancellationRequested){break;}
                catch(LiveFlyProtocolException e){Failed(e,shouldRetry);}
                catch(Exception e){if(!token.IsCancellationRequested)Failed(e,shouldRetry);}
                finally{lock(stateGate){activeClient?.Close();activeClient=null;workerState.TcpConnected=false;}}
                if(!shouldRetry||token.IsCancellationRequested)break;
                try{await Task.Delay(TimeSpan.FromSeconds(Math.Max(.25,retryDelay)),token);}catch(OperationCanceledException){break;}
            }
        }
        static async Task<string> ReadLine(StreamReader reader,CancellationToken token){var read=reader.ReadLineAsync();var cancelled=Task.Delay(Timeout.Infinite,token);await Task.WhenAny(read,cancelled);token.ThrowIfCancellationRequested();return await read;}
        void Set(LiveFlyConnectionStatus value,string detail,string session=null){lock(stateGate){workerState.Status=value;workerState.Detail=detail;if(session!=null)workerState.Session=session;}}
        void Connected(){lock(stateGate){workerState.TcpConnected=true;workerState.HelloReceived=false;workerState.HelloAccepted=false;}}
        void LineReceived(bool hello){lock(stateGate){workerState.RawLines++;if(hello)workerState.HelloReceived=true;else workerState.PoseLines++;}}
        void HelloAccepted(){lock(stateGate)workerState.HelloAccepted=true;}
        void Accepted(LiveFlyPose pose){lock(stateGate){workerState.Accepted++;workerState.LatestSequence=pose.Sequence;workerState.LatestSimTime=pose.SimTimeSeconds;}}
        void Rejected(){lock(stateGate)workerState.Rejected++;}
        void Failed(Exception error,bool retry)
        {
            var message=error.GetType().Name+": "+error.Message;
            lock(stateGate){workerState.LastError=message;workerState.Detail=message;workerState.Status=retry?LiveFlyConnectionStatus.ErrorRetrying:LiveFlyConnectionStatus.Error;}
            consoleErrors.Enqueue(message+"\n"+error);
        }

        void OnGUI()
        {
            var sim=posesAccepted==0?"--":latestSimTime.ToString("F6",System.Globalization.CultureInfo.InvariantCulture);
            var sequence=latestSequence<0?"--":latestSequence.ToString();
            var error=string.IsNullOrEmpty(lastProtocolParserOrTransportError)?"--":lastProtocolParserOrTransportError;
            var text="Python: "+StatusLabel()+"\n"+
                "TCP connected: "+(tcpConnected?"yes":"no")+"\n"+
                "Hello received / accepted: "+(helloReceived?"yes":"no")+" / "+(helloAccepted?"yes":"no")+"\n"+
                "Raw lines / pose lines: "+rawLinesReceived+" / "+poseLinesReceived+"\n"+
                "Poses accepted / rejected: "+posesAccepted+" / "+posesRejected+"\n"+
                "Latest sequence / sim time: "+sequence+" / "+sim+" s\n"+
                "Consumed by Update / applied to rig: "+posesConsumedByUpdate+" / "+posesAppliedToRig+"\n"+
                "Slot replacements: "+posesDroppedOrReplaced+"\n"+
                "Detail: "+statusDetail+"\nLast error: "+error;
            GUI.Box(new Rect(12,12,620,230),text);
        }

        string StatusLabel()
        {
            switch(status)
            {
                case LiveFlyConnectionStatus.AwaitingHello:return "Connected / Awaiting Hello";
                case LiveFlyConnectionStatus.AwaitingFirstPose:return "Connected / Awaiting First Pose";
                case LiveFlyConnectionStatus.Receiving:return "Receiving";
                case LiveFlyConnectionStatus.ErrorRetrying:return "Error / Retrying";
                case LiveFlyConnectionStatus.Error:return "Error";
                default:return status.ToString();
            }
        }
    }
}
