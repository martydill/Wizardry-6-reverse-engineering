using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using NUnit.Framework;

namespace CharacterRosterEditor.Tests;

[TestFixture]
public sealed class CharacterRecordIsolationTests
{
    private const int RecordSize = 0x01B0;
    private const int FirstRecordOffset = 0x18;
    private const int SlotCount = 2;

    [Test]
    public void EveryKnownField_EditIsIsolated_AndRoundTripsInRecordAndFile()
    {
        foreach (var fieldCase in BuildFieldCases())
        {
            AssertRecordRoundTrip(fieldCase);
            AssertFileRoundTrip(fieldCase);
        }
    }

    private static void AssertRecordRoundTrip(FieldCase fieldCase)
    {
        var baseline = BuildPatternedRecord(RecordSize);
        var record = CharacterRecord.FromBytes(0, baseline);
        fieldCase.Mutate(record);

        var updated = record.ToBytes(RecordSize);
        AssertOnlyAllowedOffsetsChanged(baseline, updated, fieldCase.ChangedOffsets, $"Record isolation failed: {fieldCase.Name}");

        var reread = CharacterRecord.FromBytes(0, updated);
        fieldCase.Assert(reread);
    }

    private static void AssertFileRoundTrip(FieldCase fieldCase)
    {
        var inputPath = Path.GetTempFileName();
        var outputPath = Path.GetTempFileName();
        try
        {
            var baselineFile = BuildBaselineFileBytes();
            File.WriteAllBytes(inputPath, baselineFile);

            var document = PcfileDocument.Load(inputPath);
            Assert.That(document.Records.Count, Is.GreaterThan(0), "Expected at least one record in baseline document.");

            fieldCase.Mutate(document.Records[0]);
            document.Save(outputPath);

            var updatedFile = File.ReadAllBytes(outputPath);
            var allowedAbsoluteOffsets = fieldCase.ChangedOffsets.Select(offset => FirstRecordOffset + offset).ToArray();
            AssertOnlyAllowedOffsetsChanged(
                baselineFile,
                updatedFile,
                allowedAbsoluteOffsets,
                $"File isolation failed: {fieldCase.Name}");

            var reread = PcfileDocument.Load(outputPath);
            fieldCase.Assert(reread.Records[0]);
        }
        finally
        {
            if (File.Exists(inputPath))
            {
                File.Delete(inputPath);
            }

            if (File.Exists(outputPath))
            {
                File.Delete(outputPath);
            }
        }
    }

    private static byte[] BuildBaselineFileBytes()
    {
        var headerPayload = Enumerable.Range(0, FirstRecordOffset - 6).Select(i => (byte)((i * 13 + 7) & 0xFF)).ToArray();
        var record0 = BuildPatternedRecord(RecordSize);
        var record1 = BuildPatternedRecord(RecordSize).Select(b => (byte)(b ^ 0x5A)).ToArray();

        using var ms = new MemoryStream();
        using var writer = new BinaryWriter(ms);
        writer.Write((ushort)RecordSize);
        writer.Write((ushort)SlotCount);
        writer.Write((ushort)FirstRecordOffset);
        writer.Write(headerPayload);
        writer.Write(record0);
        writer.Write(record1);
        writer.Flush();
        return ms.ToArray();
    }

    private static byte[] BuildPatternedRecord(int size)
    {
        var data = new byte[size];
        for (var i = 0; i < size; i++)
        {
            data[i] = (byte)((i * 37 + 11) & 0xFF);
        }

        return data;
    }

    private static void AssertOnlyAllowedOffsetsChanged(byte[] baseline, byte[] updated, IReadOnlyCollection<int> allowedOffsets, string context)
    {
        Assert.That(updated.Length, Is.EqualTo(baseline.Length), $"{context}: length changed unexpectedly.");
        var allowed = new HashSet<int>(allowedOffsets);

        for (var i = 0; i < baseline.Length; i++)
        {
            if (allowed.Contains(i))
            {
                continue;
            }

            Assert.That(updated[i], Is.EqualTo(baseline[i]), $"{context}: byte changed at offset 0x{i:X4}.");
        }
    }

    private static List<FieldCase> BuildFieldCases()
    {
        var cases = new List<FieldCase>
        {
            new("Name", r => r.Name = "TESTNAME", r => Assert.That(r.Name, Is.EqualTo("TESTNAME")), Range(0x000, 8)),
            new("AgeDays", r => r.AgeDays = 1234567890u, r => Assert.That(r.AgeDays, Is.EqualTo(1234567890u)), Range(0x008, 4)),
            new("HitPointsCurrent", r => r.HitPointsCurrent = 7777, r => Assert.That(r.HitPointsCurrent, Is.EqualTo((ushort)7777)), Range(0x018, 2)),
            new("HitPointsMax", r => r.HitPointsMax = 8888, r => Assert.That(r.HitPointsMax, Is.EqualTo((ushort)8888)), Range(0x01A, 2)),
            new("StaminaCurrent", r => r.StaminaCurrent = 6666, r => Assert.That(r.StaminaCurrent, Is.EqualTo((ushort)6666)), Range(0x01C, 2)),
            new("StaminaMax", r => r.StaminaMax = 9999, r => Assert.That(r.StaminaMax, Is.EqualTo((ushort)9999)), Range(0x01E, 2)),
            new("LoadCurrentTenths", r => r.LoadCurrentTenths = 1234, r => Assert.That(r.LoadCurrentTenths, Is.EqualTo((ushort)1234)), Range(0x020, 2)),
            new("LoadMaxTenths", r => r.LoadMaxTenths = 4321, r => Assert.That(r.LoadMaxTenths, Is.EqualTo((ushort)4321)), Range(0x022, 2)),
            new("Rank", r => r.Rank = 42, r => Assert.That(r.Rank, Is.EqualTo((ushort)42)), Range(0x024, 2)),
            new("Level", r => r.Level = 37, r => Assert.That(r.Level, Is.EqualTo((ushort)37)), Range(0x026, 2)),
            new("RaceId", r => r.RaceId = 9, r => Assert.That(r.RaceId, Is.EqualTo((byte)9)), new[] { 0x19D }),
            new("GenderId", r => r.GenderId = 1, r => Assert.That(r.GenderId, Is.EqualTo((byte)1)), new[] { 0x19E }),
            new("ClassId", r => r.ClassId = 13, r => Assert.That(r.ClassId, Is.EqualTo((byte)13)), new[] { 0x19F }),
            new("InventoryPage1Count", r => r.InventoryPage1Count = 4, r => Assert.That(r.InventoryPage1Count, Is.EqualTo((byte)4)), new[] { 0x1AC }),
            new("InventoryPage2Count", r => r.InventoryPage2Count = 6, r => Assert.That(r.InventoryPage2Count, Is.EqualTo((byte)6)), new[] { 0x1AD }),
        };

        for (var i = 0; i < 6; i++)
        {
            var schoolIndex = i;
            var schoolOffset = 0x028 + (schoolIndex * 4);
            cases.Add(
                new(
                    $"SpellPointsCurrent[{schoolIndex}]",
                    r => r.SpellPointsCurrent[schoolIndex] = (ushort)(200 + schoolIndex),
                    r => Assert.That(r.SpellPointsCurrent[schoolIndex], Is.EqualTo((ushort)(200 + schoolIndex))),
                    Range(schoolOffset, 2)));

            cases.Add(
                new(
                    $"SpellPointsMax[{schoolIndex}]",
                    r => r.SpellPointsMax[schoolIndex] = (ushort)(300 + schoolIndex),
                    r => Assert.That(r.SpellPointsMax[schoolIndex], Is.EqualTo((ushort)(300 + schoolIndex))),
                    Range(schoolOffset + 2, 2)));
        }

        for (var i = 0; i < 8; i++)
        {
            var statIndex = i;
            cases.Add(
                new(
                    $"Stats[{statIndex}]",
                    r => r.Stats[statIndex] = (byte)(10 + statIndex),
                    r => Assert.That(r.Stats[statIndex], Is.EqualTo((byte)(10 + statIndex))),
                    new[] { 0x12C + statIndex }));
        }

        for (var i = 0; i < 30; i++)
        {
            var skillIndex = i;
            cases.Add(
                new(
                    $"Skills[{skillIndex}]",
                    r => r.Skills[skillIndex] = (byte)(20 + skillIndex),
                    r => Assert.That(r.Skills[skillIndex], Is.EqualTo((byte)(20 + skillIndex))),
                    new[] { 0x134 + skillIndex }));
        }

        for (var i = 0; i < 12; i++)
        {
            var spellByteIndex = i;
            cases.Add(
                new(
                    $"KnownSpellsBitset[{spellByteIndex}]",
                    r => r.KnownSpellsBitset[spellByteIndex] = (byte)(0xA0 + spellByteIndex),
                    r => Assert.That(r.KnownSpellsBitset[spellByteIndex], Is.EqualTo((byte)(0xA0 + spellByteIndex))),
                    new[] { 0x188 + spellByteIndex }));
        }

        for (var slot = 0; slot < 20; slot++)
        {
            var slotIndex = slot;
            var baseOffset = 0x040 + (slotIndex * 8);
            cases.Add(
                new(
                    $"Inventory[{slotIndex}].ItemId",
                    r => r.Inventory[slotIndex].ItemId = (ushort)(500 + slotIndex),
                    r => Assert.That(r.Inventory[slotIndex].ItemId, Is.EqualTo((ushort)(500 + slotIndex))),
                    Range(baseOffset, 2)));
            cases.Add(
                new(
                    $"Inventory[{slotIndex}].LoadTenths",
                    r => r.Inventory[slotIndex].LoadTenths = (ushort)(600 + slotIndex),
                    r => Assert.That(r.Inventory[slotIndex].LoadTenths, Is.EqualTo((ushort)(600 + slotIndex))),
                    Range(baseOffset + 2, 2)));
            cases.Add(
                new(
                    $"Inventory[{slotIndex}].Byte4",
                    r => r.Inventory[slotIndex].Byte4 = (byte)(0x40 + slotIndex),
                    r => Assert.That(r.Inventory[slotIndex].Byte4, Is.EqualTo((byte)(0x40 + slotIndex))),
                    new[] { baseOffset + 4 }));
            cases.Add(
                new(
                    $"Inventory[{slotIndex}].Byte5",
                    r => r.Inventory[slotIndex].Byte5 = (byte)(0x50 + slotIndex),
                    r => Assert.That(r.Inventory[slotIndex].Byte5, Is.EqualTo((byte)(0x50 + slotIndex))),
                    new[] { baseOffset + 5 }));
            cases.Add(
                new(
                    $"Inventory[{slotIndex}].Byte6",
                    r => r.Inventory[slotIndex].Byte6 = (byte)(0x60 + slotIndex),
                    r => Assert.That(r.Inventory[slotIndex].Byte6, Is.EqualTo((byte)(0x60 + slotIndex))),
                    new[] { baseOffset + 6 }));
            cases.Add(
                new(
                    $"Inventory[{slotIndex}].Byte7",
                    r => r.Inventory[slotIndex].Byte7 = (byte)(0x70 + slotIndex),
                    r => Assert.That(r.Inventory[slotIndex].Byte7, Is.EqualTo((byte)(0x70 + slotIndex))),
                    new[] { baseOffset + 7 }));
        }

        return cases;
    }

    private static int[] Range(int start, int count)
    {
        var result = new int[count];
        for (var i = 0; i < count; i++)
        {
            result[i] = start + i;
        }

        return result;
    }

    private sealed class FieldCase
    {
        public FieldCase(string name, Action<CharacterRecord> mutate, Action<CharacterRecord> assert, int[] changedOffsets)
        {
            Name = name;
            Mutate = mutate;
            Assert = assert;
            ChangedOffsets = changedOffsets;
        }

        public string Name { get; }

        public Action<CharacterRecord> Mutate { get; }

        public Action<CharacterRecord> Assert { get; }

        public IReadOnlyCollection<int> ChangedOffsets { get; }
    }
}
