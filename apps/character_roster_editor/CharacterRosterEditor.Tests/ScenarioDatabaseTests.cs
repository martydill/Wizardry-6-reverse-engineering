using System;
using System.IO;
using System.Text;
using NUnit.Framework;

namespace CharacterRosterEditor.Tests;

[TestFixture]
public sealed class ScenarioDatabaseTests
{
    [Test]
    public void FromBytes_ParsesItemMetadataFromScenarioItemTable()
    {
        var bytes = new byte[0x0380 + (74 * 3)];
        var itemOffset = 0x0380 + (2 * 74);

        Encoding.ASCII.GetBytes("CHAIN=DESPAIR\0").CopyTo(bytes, itemOffset);
        BitConverter.GetBytes(1234u).CopyTo(bytes, itemOffset + 0x10);
        bytes[itemOffset + 0x18] = 2;
        bytes[itemOffset + 0x1A] = 3;
        bytes[itemOffset + 0x1B] = 6;
        bytes[itemOffset + 0x1C] = unchecked((byte)-1);
        bytes[itemOffset + 0x1E] = 9;
        bytes[itemOffset + 0x3A] = 4;
        bytes[itemOffset + 0x3B] = 8;
        bytes[itemOffset + 0x3C] = 1;
        bytes[itemOffset + 0x3D] = 7;
        bytes[itemOffset + 0x46] = unchecked((byte)-2);
        bytes[itemOffset + 0x48] = 2;

        var database = ScenarioDatabase.FromBytes(bytes);

        Assert.That(database.TryGetItem(2, out var item), Is.True);
        Assert.Multiple(() =>
        {
            Assert.That(item.Name, Is.EqualTo("CHAIN of DESPAIR"));
            Assert.That(item.Price, Is.EqualTo(1234u));
            Assert.That(item.DamageRange, Is.EqualTo("5-20"));
            Assert.That(item.ToHitBonus, Is.EqualTo((sbyte)-1));
            Assert.That(item.WeightTenths, Is.EqualTo((byte)9));
            Assert.That(item.AcBonus, Is.EqualTo((sbyte)-2));
            Assert.That(item.WeaponSkill, Is.EqualTo((byte)4));
            Assert.That(item.EquipSlot, Is.EqualTo((byte)1));
        });
    }

    [Test]
    public void FromBytes_Throws_WhenFileIsTooSmallForItemTable()
    {
        Assert.That(() => ScenarioDatabase.FromBytes(new byte[100]), Throws.InstanceOf<InvalidDataException>());
    }
}
