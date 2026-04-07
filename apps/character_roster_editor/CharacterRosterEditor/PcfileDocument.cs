using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace CharacterRosterEditor;

internal sealed class PcfileDocument
{
    public const int DefaultRecordSize = 0x01B0;
    public const int HeaderSize = 0x18;

    public ushort RecordSize { get; private set; }

    public ushort SlotCount { get; private set; }

    public ushort FirstRecordOffset { get; private set; }

    public byte[] RawHeaderBytes { get; private set; } = Array.Empty<byte>();

    public List<CharacterRecord> Records { get; } = new List<CharacterRecord>();

    public static PcfileDocument Load(string path)
    {
        var bytes = File.ReadAllBytes(path);
        if (bytes.Length < HeaderSize)
        {
            throw new InvalidDataException("File is too small to be a valid PCFILE.DBS.");
        }

        var doc = new PcfileDocument();

        using (var reader = new BinaryReader(new MemoryStream(bytes), Encoding.ASCII, leaveOpen: true))
        {
            doc.RecordSize = reader.ReadUInt16();
            doc.SlotCount = reader.ReadUInt16();
            doc.FirstRecordOffset = reader.ReadUInt16();

            var remainingHeader = doc.FirstRecordOffset - 6;
            if (remainingHeader < 0)
            {
                throw new InvalidDataException("First record offset is invalid.");
            }

            doc.RawHeaderBytes = reader.ReadBytes(remainingHeader);

            for (var slot = 0; slot < doc.SlotCount; slot++)
            {
                var offset = doc.FirstRecordOffset + (slot * doc.RecordSize);
                if (offset + doc.RecordSize > bytes.Length)
                {
                    break;
                }

                reader.BaseStream.Position = offset;
                var rawRecord = reader.ReadBytes(doc.RecordSize);
                var record = CharacterRecord.FromBytes(slot, rawRecord);
                doc.Records.Add(record);
            }
        }

        return doc;
    }

    public void Save(string path)
    {
        if (RecordSize == 0)
        {
            RecordSize = DefaultRecordSize;
        }

        if (FirstRecordOffset == 0)
        {
            FirstRecordOffset = HeaderSize;
        }

        if (SlotCount == 0)
        {
            SlotCount = (ushort)Records.Count;
        }

        using (var stream = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.None))
        using (var writer = new BinaryWriter(stream, Encoding.ASCII))
        {
            writer.Write(RecordSize);
            writer.Write((ushort)Records.Count);
            writer.Write(FirstRecordOffset);

            var headerPayloadLength = FirstRecordOffset - 6;
            var header = RawHeaderBytes ?? Array.Empty<byte>();
            if (header.Length < headerPayloadLength)
            {
                header = header.Concat(new byte[headerPayloadLength - header.Length]).ToArray();
            }

            writer.Write(header, 0, headerPayloadLength);

            foreach (var record in Records)
            {
                var raw = record.ToBytes(RecordSize);
                writer.Write(raw);
            }
        }
    }
}
