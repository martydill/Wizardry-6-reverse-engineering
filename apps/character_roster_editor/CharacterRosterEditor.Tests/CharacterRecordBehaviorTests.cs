using System;
using System.IO;
using System.Linq;
using NUnit.Framework;

namespace CharacterRosterEditor.Tests;

[TestFixture]
public sealed class CharacterRecordBehaviorTests
{
    [Test]
    public void FromBytes_Throws_WhenRecordIsTooSmall()
    {
        var tooSmall = new byte[0x01AF];
        Assert.That(() => CharacterRecord.FromBytes(0, tooSmall), Throws.InstanceOf<InvalidDataException>());
    }

    [Test]
    public void Clear_ResetsAllMutableFields()
    {
        var seededBytes = Enumerable.Repeat((byte)0xAB, 0x01B0).ToArray();
        var record = CharacterRecord.FromBytes(2, seededBytes);

        record.Clear();

        Assert.Multiple(() =>
        {
            Assert.That(record.Name, Is.EqualTo(string.Empty));
            Assert.That(record.AgeDays, Is.EqualTo(0u));
            Assert.That(record.AgeYears, Is.EqualTo(0));
            Assert.That(record.IsActive, Is.False);
            Assert.That(record.Stats, Is.All.EqualTo((byte)0));
            Assert.That(record.Skills, Is.All.EqualTo((byte)0));
            Assert.That(record.KnownSpellsBitset, Is.All.EqualTo((byte)0));
            Assert.That(record.SpellPointsCurrent, Is.All.EqualTo((ushort)0));
            Assert.That(record.SpellPointsMax, Is.All.EqualTo((ushort)0));
            Assert.That(record.PortraitIndex, Is.EqualTo((byte)0));
            Assert.That(record.Inventory.All(i => i.ItemId == 0 && i.LoadTenths == 0 && i.Byte4 == 0 && i.Byte5 == 0 && i.Byte6 == 0 && i.Byte7 == 0), Is.True);
            Assert.That(record.RawRecordBytes.Length, Is.EqualTo(0x01B0));
            Assert.That(record.RawRecordBytes, Is.All.EqualTo((byte)0));
        });
    }

    [Test]
    public void DisplayNameLookups_ReturnUnknownForUnmappedValues()
    {
        var record = CharacterRecord.FromBytes(0, new byte[0x01B0]);
        record.RaceId = 0xFE;
        record.GenderId = 0xFD;
        record.ClassId = 0xFC;

        Assert.Multiple(() =>
        {
            Assert.That(record.GetRaceDisplayName(), Is.EqualTo("Unknown (254)"));
            Assert.That(record.GetGenderDisplayName(), Is.EqualTo("Unknown (253)"));
            Assert.That(record.GetClassDisplayName(), Is.EqualTo("Unknown (252)"));
        });
    }

    [Test]
    public void IsActive_IsFalseForWhitespaceName_AndAgeYearsUsesWholeYears()
    {
        var bytes = new byte[0x01B0];
        var record = CharacterRecord.FromBytes(0, bytes);

        record.Name = "   ";
        record.AgeDays = 800;

        Assert.Multiple(() =>
        {
            Assert.That(record.IsActive, Is.False);
            Assert.That(record.AgeYears, Is.EqualTo(2));
        });
    }
}
