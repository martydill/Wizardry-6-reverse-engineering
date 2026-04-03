using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace CharacterRosterEditor;

internal sealed class CharacterRecord
{
    private const int RecordSize = 0x01B0;
    private const int InventoryOffset = 0x040;
    private const int InventoryEntrySize = 8;
    private const int InventoryEntryCount = 20;

    public int SlotIndex { get; private set; }

    public string Name { get; set; } = string.Empty;

    public uint AgeDays { get; set; }

    public ushort HitPointsCurrent { get; set; }

    public ushort HitPointsMax { get; set; }

    public ushort StaminaCurrent { get; set; }

    public ushort StaminaMax { get; set; }

    public ushort LoadCurrentTenths { get; set; }

    public ushort LoadMaxTenths { get; set; }

    public ushort Rank { get; set; }

    public ushort Level { get; set; }

    public ushort[] SpellPointsCurrent { get; } = new ushort[6];

    public ushort[] SpellPointsMax { get; } = new ushort[6];

    public byte RaceId { get; set; }

    public byte GenderId { get; set; }

    public byte ClassId { get; set; }

    public byte[] Stats { get; } = new byte[8];

    public byte[] Skills { get; } = new byte[30];

    public byte[] KnownSpellsBitset { get; } = new byte[12];

    public InventoryEntry[] Inventory { get; } = Enumerable.Range(0, InventoryEntryCount).Select(_ => new InventoryEntry()).ToArray();

    public byte InventoryPage1Count { get; set; }

    public byte InventoryPage2Count { get; set; }

    public byte[] RawRecordBytes { get; private set; } = new byte[RecordSize];

    public bool IsActive => !string.IsNullOrWhiteSpace(Name);

    public int AgeYears => (int)(AgeDays / 365u);

    public void Clear()
    {
        Name = string.Empty;
        AgeDays = 0;
        HitPointsCurrent = 0;
        HitPointsMax = 0;
        StaminaCurrent = 0;
        StaminaMax = 0;
        LoadCurrentTenths = 0;
        LoadMaxTenths = 0;
        Rank = 0;
        Level = 0;
        RaceId = 0;
        GenderId = 0;
        ClassId = 0;
        InventoryPage1Count = 0;
        InventoryPage2Count = 0;

        Array.Clear(SpellPointsCurrent, 0, SpellPointsCurrent.Length);
        Array.Clear(SpellPointsMax, 0, SpellPointsMax.Length);
        Array.Clear(Stats, 0, Stats.Length);
        Array.Clear(Skills, 0, Skills.Length);
        Array.Clear(KnownSpellsBitset, 0, KnownSpellsBitset.Length);

        foreach (var entry in Inventory)
        {
            entry.ItemId = 0;
            entry.LoadTenths = 0;
            entry.Byte4 = 0;
            entry.Byte5 = 0;
            entry.Byte6 = 0;
            entry.Byte7 = 0;
        }

        RawRecordBytes = new byte[RecordSize];
    }

    public static CharacterRecord FromBytes(int slotIndex, byte[] data)
    {
        if (data.Length < RecordSize)
        {
            throw new InvalidDataException($"Character record must be {RecordSize} bytes.");
        }

        var record = new CharacterRecord
        {
            SlotIndex = slotIndex,
            RawRecordBytes = data.ToArray(),
            Name = ReadFixedString(data, 0x000, 8),
            AgeDays = BitConverter.ToUInt32(data, 0x008),
            HitPointsCurrent = BitConverter.ToUInt16(data, 0x018),
            HitPointsMax = BitConverter.ToUInt16(data, 0x01A),
            StaminaCurrent = BitConverter.ToUInt16(data, 0x01C),
            StaminaMax = BitConverter.ToUInt16(data, 0x01E),
            LoadCurrentTenths = BitConverter.ToUInt16(data, 0x020),
            LoadMaxTenths = BitConverter.ToUInt16(data, 0x022),
            Rank = BitConverter.ToUInt16(data, 0x024),
            Level = BitConverter.ToUInt16(data, 0x026),
            RaceId = data[0x19D],
            GenderId = data[0x19E],
            ClassId = data[0x19F],
        };

        Buffer.BlockCopy(data, 0x12C, record.Stats, 0, 8);
        Buffer.BlockCopy(data, 0x134, record.Skills, 0, 30);
        Buffer.BlockCopy(data, 0x188, record.KnownSpellsBitset, 0, 12);
        record.InventoryPage1Count = data[0x1AC];
        record.InventoryPage2Count = data[0x1AD];

        for (var i = 0; i < 6; i++)
        {
            var schoolOffset = 0x028 + (i * 4);
            record.SpellPointsCurrent[i] = BitConverter.ToUInt16(data, schoolOffset);
            record.SpellPointsMax[i] = BitConverter.ToUInt16(data, schoolOffset + 2);
        }

        for (var i = 0; i < InventoryEntryCount; i++)
        {
            var offset = InventoryOffset + (i * InventoryEntrySize);
            var entry = record.Inventory[i];
            entry.ItemId = BitConverter.ToUInt16(data, offset);
            entry.LoadTenths = BitConverter.ToUInt16(data, offset + 2);
            entry.Byte4 = data[offset + 4];
            entry.Byte5 = data[offset + 5];
            entry.Byte6 = data[offset + 6];
            entry.Byte7 = data[offset + 7];
        }

        return record;
    }

    public byte[] ToBytes(int targetRecordSize)
    {
        var result = RawRecordBytes.ToArray();
        if (result.Length < targetRecordSize)
        {
            Array.Resize(ref result, targetRecordSize);
        }

        WriteFixedString(result, 0x000, 8, Name);
        WriteUInt32(result, 0x008, AgeDays);
        WriteUInt16(result, 0x018, HitPointsCurrent);
        WriteUInt16(result, 0x01A, HitPointsMax);
        WriteUInt16(result, 0x01C, StaminaCurrent);
        WriteUInt16(result, 0x01E, StaminaMax);
        WriteUInt16(result, 0x020, LoadCurrentTenths);
        WriteUInt16(result, 0x022, LoadMaxTenths);
        WriteUInt16(result, 0x024, Rank);
        WriteUInt16(result, 0x026, Level);
        result[0x1AC] = InventoryPage1Count;
        result[0x1AD] = InventoryPage2Count;

        result[0x19D] = RaceId;
        result[0x19E] = GenderId;
        result[0x19F] = ClassId;

        Buffer.BlockCopy(Stats, 0, result, 0x12C, 8);
        Buffer.BlockCopy(Skills, 0, result, 0x134, 30);
        Buffer.BlockCopy(KnownSpellsBitset, 0, result, 0x188, 12);

        for (var i = 0; i < 6; i++)
        {
            var schoolOffset = 0x028 + (i * 4);
            WriteUInt16(result, schoolOffset, SpellPointsCurrent[i]);
            WriteUInt16(result, schoolOffset + 2, SpellPointsMax[i]);
        }

        for (var i = 0; i < InventoryEntryCount; i++)
        {
            var offset = InventoryOffset + (i * InventoryEntrySize);
            var entry = Inventory[i];
            WriteUInt16(result, offset, entry.ItemId);
            WriteUInt16(result, offset + 2, entry.LoadTenths);
            result[offset + 4] = entry.Byte4;
            result[offset + 5] = entry.Byte5;
            result[offset + 6] = entry.Byte6;
            result[offset + 7] = entry.Byte7;
        }

        return result;
    }

    public string GetRaceDisplayName() => LookupTables.Races.TryGetValue(RaceId, out var value) ? value : $"Unknown ({RaceId})";

    public string GetGenderDisplayName() => LookupTables.Genders.TryGetValue(GenderId, out var value) ? value : $"Unknown ({GenderId})";

    public string GetClassDisplayName() => LookupTables.Classes.TryGetValue(ClassId, out var value) ? value : $"Unknown ({ClassId})";

    private static string ReadFixedString(byte[] data, int offset, int length)
    {
        var text = Encoding.ASCII.GetString(data, offset, length);
        return text.TrimEnd('\0', ' ');
    }

    private static void WriteFixedString(byte[] data, int offset, int length, string text)
    {
        var bytes = Encoding.ASCII.GetBytes((text ?? string.Empty).PadRight(length, '\0').Substring(0, length));
        Buffer.BlockCopy(bytes, 0, data, offset, length);
    }

    private static void WriteUInt16(byte[] data, int offset, ushort value)
    {
        var bytes = BitConverter.GetBytes(value);
        Buffer.BlockCopy(bytes, 0, data, offset, 2);
    }

    private static void WriteUInt32(byte[] data, int offset, uint value)
    {
        var bytes = BitConverter.GetBytes(value);
        Buffer.BlockCopy(bytes, 0, data, offset, 4);
    }
}

internal sealed class InventoryEntry
{
    public ushort ItemId { get; set; }

    public ushort LoadTenths { get; set; }

    public byte Byte4 { get; set; }

    public byte Byte5 { get; set; }

    public byte Byte6 { get; set; }

    public byte Byte7 { get; set; }
}

internal static class LookupTables
{
    public static readonly IReadOnlyDictionary<byte, string> Genders = new Dictionary<byte, string>
    {
        [0] = "Male",
        [1] = "Female",
    };

    public static readonly IReadOnlyDictionary<byte, string> Races = new Dictionary<byte, string>
    {
        [0] = "Human",
        [1] = "Elf",
        [2] = "Dwarf",
        [3] = "Gnome",
        [4] = "Hobbit",
        [5] = "Faerie",
        [6] = "Lizardman",
        [7] = "Dracon",
        [8] = "Felpurr",
        [9] = "Rawulf",
        [10] = "Mook",
        [11] = "Trynnie",
    };

    public static readonly IReadOnlyDictionary<byte, string> Classes = new Dictionary<byte, string>
    {
        [0] = "Fighter",
        [1] = "Mage",
        [2] = "Priest",
        [3] = "Thief",
        [4] = "Ranger",
        [5] = "Alchemist",
        [6] = "Bishop",
        [7] = "Psionic",
        [8] = "Valkyrie",
        [9] = "Bard",
        [10] = "Samurai",
        [11] = "Lord",
        [12] = "Monk",
        [13] = "Ninja",
    };
}
