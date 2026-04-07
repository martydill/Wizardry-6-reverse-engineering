using System;
using System.IO;
using NUnit.Framework;

namespace CharacterRosterEditor.Tests;

[TestFixture]
public sealed class PcfileDocumentTests
{
    [Test]
    public void Load_Throws_WhenFileIsTooSmall()
    {
        var path = Path.GetTempFileName();
        try
        {
            File.WriteAllBytes(path, new byte[10]);
            Assert.That(() => PcfileDocument.Load(path), Throws.InstanceOf<InvalidDataException>());
        }
        finally
        {
            if (File.Exists(path))
            {
                File.Delete(path);
            }
        }
    }

    [Test]
    public void Save_UsesDefaults_AndPadsHeaderBytes()
    {
        var path = Path.GetTempFileName();
        try
        {
            var document = new PcfileDocument();
            var record = CharacterRecord.FromBytes(0, new byte[PcfileDocument.DefaultRecordSize]);
            record.Name = "ALICE";
            document.Records.Add(record);

            document.Save(path);

            var reloaded = PcfileDocument.Load(path);
            Assert.Multiple(() =>
            {
                Assert.That(reloaded.RecordSize, Is.EqualTo(PcfileDocument.DefaultRecordSize));
                Assert.That(reloaded.FirstRecordOffset, Is.EqualTo(PcfileDocument.HeaderSize));
                Assert.That(reloaded.RawHeaderBytes.Length, Is.EqualTo(PcfileDocument.HeaderSize - 6));
                Assert.That(reloaded.Records.Count, Is.EqualTo(1));
                Assert.That(reloaded.Records[0].Name, Is.EqualTo("ALICE"));
            });
        }
        finally
        {
            if (File.Exists(path))
            {
                File.Delete(path);
            }
        }
    }

    [Test]
    public void Load_StopsAtTruncatedSlotData()
    {
        var path = Path.GetTempFileName();
        try
        {
            using (var stream = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.None))
            using (var writer = new BinaryWriter(stream))
            {
                writer.Write((ushort)PcfileDocument.DefaultRecordSize);
                writer.Write((ushort)2);
                writer.Write((ushort)PcfileDocument.HeaderSize);
                writer.Write(new byte[PcfileDocument.HeaderSize - 6]);
                writer.Write(new byte[PcfileDocument.DefaultRecordSize]);
            }

            var loaded = PcfileDocument.Load(path);
            Assert.That(loaded.Records.Count, Is.EqualTo(1));
        }
        finally
        {
            if (File.Exists(path))
            {
                File.Delete(path);
            }
        }
    }
}
