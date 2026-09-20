using System.IO;
using FlyBrain.M7FReplay;
using NUnit.Framework;

namespace FlyBrain.Tests
{
    public sealed class M7FReplayTests
    {
        static byte[] Fixture()
        {
            using var stream = new MemoryStream(); using var writer = new BinaryWriter(stream);
            writer.Write(System.Text.Encoding.ASCII.GetBytes(M7FReplayData.Magic));
            writer.Write((uint)1); writer.Write((uint)6); writer.Write((uint)1); writer.Write((uint)11);
            for (var i = 0; i < 6; i++) writer.Write(i * .1);            // time
            for (var i = 0; i < 18; i++) writer.Write((double)i);       // position
            for (var i = 0; i < 24; i++) writer.Write(i % 4 == 0 ? 1d : 0d); // quaternion
            for (var i = 0; i < 252; i++) writer.Write(i * .001);       // joints
            writer.Write(.5);                                           // neural time
            for (var i = 0; i < 11 * 3; i++) writer.Write((double)i);   // observer/decoder/applied
            for (var i = 0; i < 6; i++) writer.Write((double)i);        // sensory
            writer.Write((long)7); writer.Write((long)9);
            return stream.ToArray();
        }

        [Test] public void LoaderPreservesCanonicalValuesAndIndexesNeuralCadence()
        {
            var replay = M7FReplayLoader.Read(Fixture());
            Assert.That(replay.PhysicsCount, Is.EqualTo(6)); Assert.That(replay.NeuralCount, Is.EqualTo(1));
            Assert.That(replay.PhysicsTime[5], Is.EqualTo(.5)); Assert.That(replay.JointPosition[251], Is.EqualTo(.251));
            Assert.That(replay.NeuralIndexForFrame(5), Is.Zero);
        }

        [Test] public void CoordinateConversionUsesValidatedProjectConvention()
        {
            var replay = M7FReplayLoader.Read(Fixture());
            Assert.That(replay.UnityPosition(1).x, Is.EqualTo(.3f).Within(1e-6));
            Assert.That(replay.UnityPosition(1).y, Is.EqualTo(.5f).Within(1e-6));
            Assert.That(replay.UnityPosition(1).z, Is.EqualTo(.4f).Within(1e-6));
        }

        [Test] public void TruncatedBinaryFailsClosed()
        {
            var bytes = Fixture(); System.Array.Resize(ref bytes, bytes.Length - 1);
            Assert.Throws<InvalidDataException>(() => M7FReplayLoader.Read(bytes));
        }
    }
}
