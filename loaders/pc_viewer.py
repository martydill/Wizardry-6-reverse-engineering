"""Dump the full contents of PCFILE.DBS.

Usage:
    python loaders/pc_viewer.py <path/to/PCFILE.DBS> [--all] [--hex]

    --all   also show empty/inactive slots
    --hex   append a hex dump of each printed record
"""

from __future__ import annotations

import argparse
import logging
import textwrap
from pathlib import Path

from bane.data.pcfile_editor import (
    PCFileEditor,
    STAT_NAMES,
    SKILL_NAMES,
    SPELL_SCHOOLS,
    AGE_RAW_OFFSET,
    HP_OFFSET,
    STAMINA_OFFSET,
    GOLD_OFFSET,
    XP_OFFSET,
    SPELL_KNOWN_BLOCK_OFFSET,
    SPELL_KNOWN_BLOCK_SIZE,
    PORTRAIT_OFFSET,
    STAT_BLOCK_OFFSET,
    STAT_BLOCK_SIZE,
    RACE_NAMES_INTERNAL,
    CLASS_NAMES_INTERNAL,
)
from bane.data.pcfile_spell_catalog import (
    SPELL_DEF_BY_ID,
    known_spell_ids_from_block,
)
from bane.data.scenario_parser import ScenarioParser


# ---------------------------------------------------------------------------
# Additional field offsets not exposed by the editor as properties
# ---------------------------------------------------------------------------
# +0x08..+0x0B  : 32-bit age counter (low word at +0x08, high word at +0x0A)
# +0x18..+0x19  : HP current
# +0x1A..+0x1B  : HP max
# +0x1C..+0x1D  : stamina current
# +0x1E..+0x1F  : stamina max
# +0x20..+0x21  : current load / encumbrance
# +0x22..+0x23  : max load / encumbrance capacity

_EXTRA_FIELDS: list[tuple[int, str]] = [
    (0x0C, "unk_0x0C"),
    (0x0E, "unk_0x0E"),
    (0x10, "unk_0x10"),
    (0x12, "unk_0x12"),
    (0x14, "unk_0x14"),
    (0x16, "unk_0x16"),
    (0x24, "rank"),
    (0x26, "level"),
    (0x19C, "portrait_index"),
    (0x1A5, "viewer_cached_0x1A5"),
    (0x1A9, "viewer_input_0x1A9"),
    (0x1AA, "viewer_input_0x1AA"),
    (0x1AC, "inventory_page1_count"),
    (0x1AD, "inventory_page2_count"),
]


def _u16(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 2], "little")


def _u32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 4], "little")


def _hexdump(data: bytes | bytearray, base_offset: int = 0, width: int = 16) -> str:
    lines: list[str] = []
    for row_start in range(0, len(data), width):
        chunk = data[row_start:row_start + width]
        hex_part = " ".join(f"{b:02X}" for b in chunk)
        asc_part = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in chunk)
        lines.append(f"  {base_offset + row_start:04X}  {hex_part:<{width * 3}}  {asc_part}")
    return "\n".join(lines)


def _iter_inventory_entries(record_data: bytes | bytearray) -> list[tuple[int, bytes | bytearray]]:
    out: list[tuple[int, bytes | bytearray]] = []
    page1 = record_data[0x1AC]
    page2 = record_data[0x1AD] if 0x1AD < len(record_data) else 0

    for slot in range(max(0, min(page1, 10))):
        off = 0x40 + slot * 8
        out.append((slot, record_data[off:off + 8]))

    for slot in range(max(0, min(page2, 10))):
        idx = 10 + slot
        off = 0x40 + idx * 8
        out.append((idx, record_data[off:off + 8]))

    return out


def dump_record(record, *, show_hex: bool, item_defs: dict[int, object] | None) -> None:
    d = record.data
    gender_str = "Female" if record.gender else "Male"
    gender_ch = "F" if record.gender else "M"
    age_raw32 = _u32(d, AGE_RAW_OFFSET)
    age_years = age_raw32 // 365
    age_days_remainder = age_raw32 % 365
    print(
        f"  {record.name!r}  {record.class_name}#{record.class_id}  "
        f"{record.race_name}#{record.race_id}  {gender_str}({gender_ch})  "
        f"Portrait={d[PORTRAIT_OFFSET]}  Age={age_years}y + {age_days_remainder}d"
    )
    print(
        f"  HP={record.hp}/{_u16(d, HP_OFFSET + 2)}  "
        f"STM={record.stamina}/{_u16(d, STAMINA_OFFSET + 2)}  "
        f"Load={record.gold}/{record.experience}  "
        f"AgeRaw={age_raw32} (0x{age_raw32:08X})  "
        f"AgeWords=0x{_u16(d, AGE_RAW_OFFSET):04X}/0x{_u16(d, AGE_RAW_OFFSET + 2):04X}"
    )

    stats = record.stats
    stat_parts = [f"{name[:3].upper()}={stats[name]}" for name in STAT_NAMES]
    print(f"  Stats       : {'  '.join(stat_parts)}")

    school_parts: list[str] = []
    any_school_points = False
    for school, offset in SPELL_SCHOOLS:
        current = _u16(d, offset)
        maximum = _u16(d, offset + 2)
        if not current and not maximum:
            continue
        any_school_points = True
        school_parts.append(f"{school.title()}={current}/{maximum}")
    if not any_school_points:
        print("  Spell Points: (none)")
    else:
        print(f"  Spell Points: {'  '.join(school_parts)}")

    known_spell_ids = known_spell_ids_from_block(
        d,
        offset=SPELL_KNOWN_BLOCK_OFFSET,
        size=SPELL_KNOWN_BLOCK_SIZE,
    )
    if not known_spell_ids:
        print("  Known Spells: (none)")
    else:
        spell_parts: list[str] = []
        for spell_id in known_spell_ids:
            spell = SPELL_DEF_BY_ID.get(spell_id)
            if spell is None:
                spell_parts.append(f"[{spell_id:02d}]<?>")
                continue
            spell_parts.append(f"[{spell.id:02d}] {spell.name} ({spell.sphere} L{spell.level} M{spell.mana})")
        print(f"  Known Spells: {'; '.join(spell_parts)}")

    skills = record.skills
    if skills:
        skill_parts = []
        for skill_name, val in skills.items():
            label = skill_name.replace("_", " ").title()
            skill_parts.append(f"{label}={val}")
        print(f"  Skills      : {'; '.join(skill_parts)}")
    else:
        print("  Skills      : (none)")

    extra_parts: list[str] = []
    for offset, label in _EXTRA_FIELDS:
        if offset >= len(d):
            continue
        if offset in {0x19C, 0x1A5, 0x1A9, 0x1AA, 0x1AC, 0x1AD}:
            val8 = d[offset]
            if val8:
                extra_parts.append(f"+0x{offset:03X} {label}={val8} (0x{val8:02X})")
            continue
        val16 = _u16(d, offset)
        if val16:
            extra_parts.append(f"+0x{offset:03X} {label}={val16} (0x{val16:04X})")
    if extra_parts:
        print(f"  Other Words : {'; '.join(extra_parts)}")
    else:
        print("  Other Words : (none)")

    entries = _iter_inventory_entries(d)
    if not entries:
        print("  Inventory   : (none)")
    else:
        print("  Inventory   :")
        for slot_idx, entry in entries:
            item_id = _u16(entry, 0)
            weight_x10 = _u16(entry, 2)
            b4, b5, b6, b7 = entry[4], entry[5], entry[6], entry[7]
            item = item_defs.get(item_id) if item_defs else None
            item_name = getattr(item, "name", f"item_{item_id}")
            item_type = getattr(item, "item_type", None)
            item_type_name = getattr(item_type, "name", "?") if item_type is not None else "?"
            print(
                f"    {slot_idx:02d}  id={item_id:>3}  {item_name:<20} "
                f"{item_type_name:<10} wt={weight_x10 / 10:.1f}  "
                f"b4=0x{b4:02X} b5=0x{b5:02X} b6=0x{b6:02X} b7=0x{b7:02X}"
            )

    if show_hex:
        print("  Raw hex dump:")
        print(_hexdump(d))


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump PCFILE.DBS character records")
    parser.add_argument("path", type=Path, help="Path to PCFILE.DBS")
    parser.add_argument(
        "--all", dest="show_all", action="store_true",
        help="Show all slots, including empty ones"
    )
    parser.add_argument(
        "--hex", dest="show_hex", action="store_true",
        help="Append hex dump of each record"
    )
    args = parser.parse_args()

    editor = PCFileEditor.from_file(args.path)
    item_defs: dict[int, object] = {}
    scenario_path = args.path.with_name("SCENARIO.DBS")
    if scenario_path.exists():
        try:
            logging.getLogger("bane.data.scenario_parser").setLevel(logging.ERROR)
            item_defs = ScenarioParser(scenario_path).parse().items
        except Exception:
            item_defs = {}

    active = editor.active_records()
    print("Active characters (quick view):")
    print("-" * 60)
    for rec in active:
        stats = rec.stats
        stat_str = "  ".join(
            f"{name[:3].upper()}={stats[name]}" for name in STAT_NAMES[:6]
        )
        gender_ch = "F" if rec.gender else "M"
        print(
            f"  [{rec.slot_index:2d}] {rec.name:<8}  {rec.class_name:<10}  {rec.race_name:<12}  {gender_ch}  "
            f"HP={rec.hp:>3}/{_u16(rec.data, HP_OFFSET + 2):<3}  "
            f"SP={rec.stamina:>3}/{_u16(rec.data, STAMINA_OFFSET + 2):<3}  "
            f"Load={rec.gold:>4}/{rec.experience:<4}  {stat_str}"
        )
    print()

    records_to_dump = editor.records if args.show_all else active
    for rec in records_to_dump:
        status = "ACTIVE" if rec.is_active else "empty"
        print("=" * 60)
        print(f"Slot {rec.slot_index}  [{status}]")
        print("-" * 60)
        if rec.is_active:
            dump_record(rec, show_hex=args.show_hex, item_defs=item_defs)
        elif args.show_all:
            if args.show_hex:
                print(_hexdump(rec.data))
            else:
                print("  (no data)")
        print()


if __name__ == "__main__":
    main()
