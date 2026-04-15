using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace CharacterRosterEditor;

internal sealed class ScenarioDatabase
{
    private const int ItemTableOffset = 0x0380;
    private const int ItemRecordSize = 74;
    private const int ItemSlotCount = 483;

    private readonly Dictionary<ushort, ItemMetadata> _itemsById;

    private ScenarioDatabase(IEnumerable<ItemMetadata> items)
    {
        _itemsById = items.ToDictionary(item => item.ItemId);
    }

    public IReadOnlyDictionary<ushort, ItemMetadata> ItemsById => _itemsById;

    public static ScenarioDatabase Load(string path)
    {
        return FromBytes(File.ReadAllBytes(path));
    }

    public static ScenarioDatabase FromBytes(byte[] bytes)
    {
        if (bytes.Length < ItemTableOffset + ItemRecordSize)
        {
            throw new InvalidDataException("File is too small to contain a scenario.dbs item table.");
        }

        var items = new List<ItemMetadata>();
        for (var slot = 0; slot < ItemSlotCount; slot++)
        {
            var offset = ItemTableOffset + (slot * ItemRecordSize);
            if (offset + ItemRecordSize > bytes.Length)
            {
                break;
            }

            var item = ParseItemRecord(bytes, offset, (ushort)slot);
            if (item != null)
            {
                items.Add(item);
            }
        }

        return new ScenarioDatabase(items);
    }

    public bool TryGetItem(ushort itemId, out ItemMetadata item)
    {
        return _itemsById.TryGetValue(itemId, out item!);
    }

    private static ItemMetadata? ParseItemRecord(byte[] bytes, int offset, ushort itemId)
    {
        var name = ReadCString(bytes, offset, 16).Replace("=", " of ");
        if (string.IsNullOrWhiteSpace(name) || !name.Any(char.IsLetter))
        {
            return null;
        }

        var damageDice = bytes[offset + 0x1A];
        var damageFaces = bytes[offset + 0x1B];
        var damageBonus = bytes[offset + 0x18];

        return new ItemMetadata(
            itemId,
            name,
            BitConverter.ToUInt32(bytes, offset + 0x10),
            damageDice,
            damageFaces,
            damageBonus,
            ToSignedByte(bytes[offset + 0x1C]),
            bytes[offset + 0x1E],
            ToSignedByte(bytes[offset + 0x46]),
            bytes[offset + 0x3A],
            bytes[offset + 0x3B],
            bytes[offset + 0x3C],
            bytes[offset + 0x3D],
            bytes[offset + 0x48]);
    }

    private static string ReadCString(byte[] bytes, int offset, int maxLength)
    {
        var length = 0;
        while (length < maxLength && offset + length < bytes.Length && bytes[offset + length] != 0)
        {
            length++;
        }

        return Encoding.ASCII.GetString(bytes, offset, length);
    }

    private static sbyte ToSignedByte(byte value)
    {
        return unchecked((sbyte)value);
    }
}

internal sealed class ItemMetadata
{
    public ItemMetadata(
        ushort itemId,
        string name,
        uint price,
        byte damageDice,
        byte damageFaces,
        byte damageBonus,
        sbyte toHitBonus,
        byte weightTenths,
        sbyte acBonus,
        byte weaponSkill,
        byte handedness,
        byte equipSlot,
        byte attackModes,
        byte swings)
    {
        ItemId = itemId;
        Name = name;
        Price = price;
        DamageDice = damageDice;
        DamageFaces = damageFaces;
        DamageBonus = damageBonus;
        ToHitBonus = toHitBonus;
        WeightTenths = weightTenths;
        AcBonus = acBonus;
        WeaponSkill = weaponSkill;
        Handedness = handedness;
        EquipSlot = equipSlot;
        AttackModes = attackModes;
        Swings = swings;
    }

    public ushort ItemId { get; }

    public string Name { get; }

    public uint Price { get; }

    public byte DamageDice { get; }

    public byte DamageFaces { get; }

    public byte DamageBonus { get; }

    public sbyte ToHitBonus { get; }

    public byte WeightTenths { get; }

    public sbyte AcBonus { get; }

    public byte WeaponSkill { get; }

    public byte Handedness { get; }

    public byte EquipSlot { get; }

    public byte AttackModes { get; }

    public byte Swings { get; }

    public string DamageRange
    {
        get
        {
            if (DamageDice == 0 || DamageFaces == 0)
            {
                return string.Empty;
            }

            var minimum = DamageDice + DamageBonus;
            var maximum = (DamageDice * DamageFaces) + DamageBonus;
            return $"{minimum}-{maximum}";
        }
    }
}
