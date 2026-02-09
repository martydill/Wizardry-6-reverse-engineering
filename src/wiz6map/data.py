from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

W6MO_HEADER = b"W6MO"
W6IT_HEADER = b"W6IT"
W6NP_HEADER = b"W6NP"
W6CV_HEADER = b"W6CV"
W6GD_HEADER = b"W6GD"
W6SV_HEADER = b"W6SV"
W6PT_HEADER = b"W6PT"


class GameDataLoadError(ValueError):
    """Raised when Wizardry 6 data files cannot be parsed."""


@dataclass(frozen=True)
class RecordData:
    record_size: int
    records: tuple[bytes, ...]

    @property
    def record_count(self) -> int:
        return len(self.records)

    def record_at(self, index: int) -> bytes:
        if not (0 <= index < self.record_count):
            raise IndexError("Record index out of bounds")
        return self.records[index]


@dataclass(frozen=True)
class SaveGame:
    payload: bytes


@dataclass(frozen=True)
class PortraitSet:
    width: int
    height: int
    portraits: tuple[bytes, ...]

    def portrait_at(self, index: int) -> bytes:
        if not (0 <= index < len(self.portraits)):
            raise IndexError("Portrait index out of bounds")
        return self.portraits[index]


@dataclass(frozen=True)
class GameDataBlob:
    payload: bytes


def load_monsters(path: str | Path, *, fmt: str | None = None) -> RecordData:
    return _load_record_file(path, header=W6MO_HEADER, fmt=fmt)


def load_items(path: str | Path, *, fmt: str | None = None) -> RecordData:
    return _load_record_file(path, header=W6IT_HEADER, fmt=fmt)


def load_npcs(path: str | Path, *, fmt: str | None = None) -> RecordData:
    return _load_record_file(path, header=W6NP_HEADER, fmt=fmt)


def load_conversations(path: str | Path, *, fmt: str | None = None) -> RecordData:
    return _load_record_file(path, header=W6CV_HEADER, fmt=fmt)


def load_game_data(path: str | Path, *, fmt: str | None = None) -> GameDataBlob:
    data = Path(path).read_bytes()
    if not data:
        raise GameDataLoadError("Game data file is empty")

    if fmt == "w6gd" or (fmt is None and data.startswith(W6GD_HEADER)):
        return GameDataBlob(payload=data[4:])

    if fmt == "raw":
        return GameDataBlob(payload=data)

    if fmt is not None:
        raise GameDataLoadError(f"Unknown format: {fmt}")

    raise GameDataLoadError("Unable to detect game data format")


def load_save_game(
    path: str | Path, *, fmt: str | None = None, expected_size: int | None = None
) -> SaveGame:
    data = Path(path).read_bytes()
    if not data:
        raise GameDataLoadError("Save game file is empty")

    payload: bytes
    if fmt == "w6sv" or (fmt is None and data.startswith(W6SV_HEADER)):
        payload = data[4:]
    elif fmt == "raw":
        payload = data
    elif fmt is not None:
        raise GameDataLoadError(f"Unknown format: {fmt}")
    else:
        raise GameDataLoadError("Unable to detect save game format")

    if expected_size is not None and len(payload) != expected_size:
        raise GameDataLoadError(
            "Save game payload length does not match expected size "
            f"({len(payload)} != {expected_size})."
        )

    return SaveGame(payload=payload)


def load_portraits(
    path: str | Path,
    *,
    fmt: str | None = None,
    width: int | None = None,
    height: int | None = None,
    count: int | None = None,
) -> PortraitSet:
    data = Path(path).read_bytes()
    if not data:
        raise GameDataLoadError("Portrait file is empty")

    if fmt == "w6pt" or (fmt is None and data.startswith(W6PT_HEADER)):
        if len(data) < 10:
            raise GameDataLoadError("W6PT header too short")
        width = int.from_bytes(data[4:6], "little")
        height = int.from_bytes(data[6:8], "little")
        count = int.from_bytes(data[8:10], "little")
        payload = data[10:]
    elif fmt == "raw":
        if width is None or height is None:
            raise GameDataLoadError("Raw portraits require width and height")
        payload = data
    elif fmt is not None:
        raise GameDataLoadError(f"Unknown format: {fmt}")
    else:
        raise GameDataLoadError("Unable to detect portrait format")

    if width is None or height is None:
        raise GameDataLoadError("Portrait dimensions are missing")

    portrait_size = width * height
    if portrait_size <= 0:
        raise GameDataLoadError("Invalid portrait dimensions")

    if count is None:
        if len(payload) % portrait_size != 0:
            raise GameDataLoadError("Portrait payload length is not a multiple of size")
        count = len(payload) // portrait_size

    expected = portrait_size * count
    if len(payload) != expected:
        raise GameDataLoadError(
            "Portrait payload length does not match expected size "
            f"({len(payload)} != {expected})."
        )

    portraits = tuple(
        payload[i : i + portrait_size] for i in range(0, expected, portrait_size)
    )
    return PortraitSet(width=width, height=height, portraits=portraits)


def load_raw_records(
    path: str | Path,
    *,
    record_size: int,
    record_count: int | None = None,
) -> RecordData:
    data = Path(path).read_bytes()
    return _load_record_payload(
        data, record_size=record_size, record_count=record_count
    )


def _load_record_file(
    path: str | Path, *, header: bytes, fmt: str | None
) -> RecordData:
    data = Path(path).read_bytes()
    if not data:
        raise GameDataLoadError("Record file is empty")

    if fmt == "raw":
        raise GameDataLoadError("Raw record format requires record_size")

    if fmt is not None and fmt != header.decode("ascii").lower():
        raise GameDataLoadError(f"Unknown format: {fmt}")

    if not data.startswith(header):
        raise GameDataLoadError("Record file header mismatch")

    if len(data) < 8:
        raise GameDataLoadError("Record header too short")

    record_size = int.from_bytes(data[4:6], "little")
    record_count = int.from_bytes(data[6:8], "little")
    payload = data[8:]
    return _load_record_payload(
        payload, record_size=record_size, record_count=record_count
    )


def _load_record_payload(
    payload: bytes, *, record_size: int, record_count: int | None
) -> RecordData:
    if record_size <= 0:
        raise GameDataLoadError("Record size must be positive")

    if record_count is None:
        if len(payload) % record_size != 0:
            raise GameDataLoadError("Record payload length is not a multiple of size")
        record_count = len(payload) // record_size

    expected = record_size * record_count
    if len(payload) != expected:
        raise GameDataLoadError(
            "Record payload length does not match expected size "
            f"({len(payload)} != {expected})."
        )

    records = tuple(
        payload[i : i + record_size] for i in range(0, expected, record_size)
    )
    return RecordData(record_size=record_size, records=records)
