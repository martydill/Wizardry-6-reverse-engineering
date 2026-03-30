from __future__ import annotations

import argparse
import math
import struct
from pathlib import Path

PIT_BASE_HZ = 1_193_180
DEFAULT_PCM_RATE = 8_000
DEFAULT_SPEAKER_OUTPUT_RATE = 44_100
DEFAULT_SPEAKER_TICK_RATE = 8_286
DEFAULT_SPEAKER_XLAT_KIND = "mode01"
DEFAULT_SPEAKER_XLAT_LEVEL = 72
DEFAULT_SPEAKER_LOWPASS_HZ = 2_500.0
DEFAULT_SPEAKER_PHASE_PARAM = 0x7E
DEFAULT_SPEAKER_MECHANICAL_HZ = 1_600.0


def infer_sound_index(path: Path) -> int | None:
    stem = path.stem.upper()
    if not stem.startswith("SOUND"):
        return None
    suffix = stem[5:]
    if not suffix.isdigit():
        return None
    return int(suffix)


def load_sound_metadata(path: Path) -> dict[str, int] | None:
    sound_index = infer_sound_index(path)
    if sound_index is None:
        return None

    gamedata = path.parent
    master_hdr = gamedata / "MASTER.HDR"
    disk_hdr = gamedata / "DISK.HDR"
    scenario_dbs = gamedata / "SCENARIO.DBS"
    if not master_hdr.exists() or not disk_hdr.exists() or not scenario_dbs.exists():
        return None

    master = master_hdr.read_bytes()
    disk = disk_hdr.read_bytes()
    scenario = scenario_dbs.read_bytes()
    opcode = 9

    size_off = opcode * 2
    base_off = 4 + opcode * 4
    if len(master) < size_off + 2 or len(disk) < base_off + 4:
        return None

    record_size = int.from_bytes(master[size_off : size_off + 2], "little")
    base = int.from_bytes(disk[base_off : base_off + 4], "little")
    record_off = base + (sound_index * record_size)
    if record_size < 12 or record_off < 0 or record_off + 12 > len(scenario):
        return None

    record = scenario[record_off : record_off + record_size]
    return {
        "phase_param": int.from_bytes(record[8:10], "little") & 0xFF,
        "xlat_level": record[10],
    }


def decode_snd(path: Path) -> bytes:
    data = path.read_bytes()
    if len(data) < 4:
        raise ValueError(f"{path} is too small to be a valid SND resource")

    tree_len = int.from_bytes(data[0:2], "little")
    if tree_len == 0:
        return data[2:]

    tree = data[2 : 2 + tree_len]
    stream = data[2 + tree_len :]
    if len(stream) < 3:
        raise ValueError(f"{path} is truncated")

    output_len = int.from_bytes(stream[0:2], "little")
    si = 2
    bit_count = 8
    current = stream[si]
    si += 1
    out = bytearray()

    while len(out) < output_len:
        cx = bit_count
        node = 0

        while True:
            carry = (current & 0x80) != 0
            current = (current << 1) & 0xFF
            edge = node + 2 if carry else node
            child = int.from_bytes(tree[edge : edge + 2], "little", signed=True)

            if child >= 0:
                node = child
                break

            node = (-child) << 2
            cx -= 1
            if cx != 0:
                continue

            cx = 8
            if si >= len(stream):
                raise ValueError(f"{path} bitstream underrun")
            current = stream[si]
            si += 1

        bit_count = cx - 1
        if bit_count < 0:
            bit_count = 8
            if si >= len(stream):
                raise ValueError(f"{path} bitstream underrun after leaf")
            current = stream[si]
            si += 1

        out.append(node & 0xFF)

        if bit_count == 0 and len(out) < output_len:
            bit_count = 8
            if si >= len(stream):
                raise ValueError(f"{path} bitstream underrun after output")
            current = stream[si]
            si += 1

    return bytes(out)


def build_xlat_table(kind: str, level: int) -> bytes:
    level = max(1, min(level, 255))

    if kind == "identity":
        return bytes(range(256))

    table = bytearray(256)
    if kind == "mode23":
        for i in range(256):
            table[i] = ((level * i) >> 8) & 0xFF
        return bytes(table)

    if kind == "mode01":
        taper = 0
        working_level = level
        if working_level >= 0x49:
            taper = (working_level - 0x49) >> 1

        for i in range(256):
            value = ((working_level * i) >> 8) - taper
            if value < 0:
                value = 0
            elif value >= working_level:
                value = working_level
            table[i] = value + 1
        return bytes(table)

    raise ValueError(f"unknown xlat table kind: {kind}")


def lowpass_alpha(cutoff_hz: float, sample_rate: int) -> float:
    if cutoff_hz <= 0:
        return 1.0
    return 1.0 - math.exp((-2.0 * math.pi * cutoff_hz) / sample_rate)


def render_pcm_approx(decoded: bytes) -> bytes:
    return decoded


def render_dac_approx(decoded: bytes, xlat_kind: str, xlat_level: int) -> bytes:
    table = build_xlat_table(xlat_kind, xlat_level)
    return bytes(table[value] for value in decoded)


def render_speaker_approx(
    decoded: bytes,
    output_rate: int,
    tick_rate: int,
    phase_param: int,
    xlat_kind: str,
    xlat_level: int,
    lowpass_hz: float,
) -> bytes:
    if not decoded:
        return b""

    table = build_xlat_table(xlat_kind, xlat_level)
    tick_period = 1.0 / tick_rate
    phase_step = (0xFF - (phase_param & 0xFF)) & 0xFF
    if phase_step == 0:
        phase_step = 0x100

    tick_byte_indices: list[int] = []
    byte_index = 0
    phase = 0
    while byte_index < len(decoded):
        tick_byte_indices.append(byte_index)
        phase += phase_step
        byte_index += phase >> 8
        phase &= 0xFF

    ticks = len(tick_byte_indices)
    duration = ticks * tick_period
    sample_count = max(1, int(math.ceil(duration * output_rate)))
    sample_period = 1.0 / output_rate
    alpha = lowpass_alpha(lowpass_hz, output_rate)
    mechanical_alpha = lowpass_alpha(min(DEFAULT_SPEAKER_MECHANICAL_HZ, lowpass_hz * 0.7), output_rate)

    filtered = 0.0
    mechanical = 0.0
    dc_blocked = 0.0
    previous_mechanical = 0.0
    pcm = bytearray()

    for sample_index in range(sample_count):
        sample_start = sample_index * sample_period
        sample_end = min(duration, sample_start + sample_period)
        if sample_end <= sample_start:
            target = filtered
        else:
            active_time = 0.0
            tick_index = min(ticks - 1, int(sample_start * tick_rate))

            while tick_index < ticks:
                tick_start = tick_index * tick_period
                if tick_start >= sample_end:
                    break

                tick_end = min(duration, tick_start + tick_period)
                overlap_start = max(sample_start, tick_start)
                overlap_end = min(sample_end, tick_end)
                if overlap_end > overlap_start:
                    byte_index = tick_byte_indices[tick_index]
                    pulse_width = max(1, table[decoded[byte_index]]) / PIT_BASE_HZ
                    pulse_end = min(tick_end, tick_start + pulse_width)
                    active_overlap = min(overlap_end, pulse_end) - overlap_start
                    if active_overlap > 0.0:
                        active_time += active_overlap

                tick_index += 1

            duty = active_time / (sample_end - sample_start)
            # PIT mode-0 plus the speaker gate behaves more like a unipolar
            # pulse train than a bipolar waveform. Averaging first and then
            # AC-coupling it produces a much less noisy modern approximation.
            target = duty

        filtered += alpha * (target - filtered)
        mechanical += mechanical_alpha * (filtered - mechanical)
        dc_blocked = mechanical - previous_mechanical + (0.995 * dc_blocked)
        previous_mechanical = mechanical
        pcm.extend(struct.pack("<h", int(max(-1.0, min(1.0, dc_blocked)) * 32767)))

    return bytes(pcm)


def play_snd(
    path: Path,
    render_mode: str = "speaker",
    sample_rate: int = 0,
    tick_rate: int = DEFAULT_SPEAKER_TICK_RATE,
    phase_param: int = DEFAULT_SPEAKER_PHASE_PARAM,
    xlat_kind: str = DEFAULT_SPEAKER_XLAT_KIND,
    xlat_level: int = DEFAULT_SPEAKER_XLAT_LEVEL,
    lowpass_hz: float = DEFAULT_SPEAKER_LOWPASS_HZ,
) -> None:
    import pygame

    decoded = decode_snd(path)
    metadata = load_sound_metadata(path)
    if metadata is not None:
        if phase_param == DEFAULT_SPEAKER_PHASE_PARAM:
            phase_param = metadata["phase_param"]
        if xlat_level == DEFAULT_SPEAKER_XLAT_LEVEL:
            xlat_level = metadata["xlat_level"]

    if render_mode == "pcm":
        audio = render_pcm_approx(decoded)
        mixer_size = 8
        mixer_rate = sample_rate if sample_rate > 0 else DEFAULT_PCM_RATE
    elif render_mode == "dac":
        audio = render_dac_approx(decoded, xlat_kind=xlat_kind, xlat_level=xlat_level)
        mixer_size = 8
        mixer_rate = sample_rate if sample_rate > 0 else DEFAULT_PCM_RATE
    elif render_mode == "speaker":
        speaker_rate = sample_rate if sample_rate > 0 else DEFAULT_SPEAKER_OUTPUT_RATE
        audio = render_speaker_approx(
            decoded,
            output_rate=speaker_rate,
            tick_rate=tick_rate,
            phase_param=phase_param,
            xlat_kind=xlat_kind,
            xlat_level=xlat_level,
            lowpass_hz=lowpass_hz,
        )
        mixer_size = -16
        mixer_rate = speaker_rate
    else:
        raise ValueError(f"unknown render mode: {render_mode}")

    pygame.mixer.init(
        frequency=mixer_rate,
        size=mixer_size,
        channels=1,
    )

    sound = pygame.mixer.Sound(buffer=audio)
    channel = sound.play()

    while channel is not None and channel.get_busy():
        pygame.time.wait(10)

    pygame.mixer.quit()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Play Wizardry 6 SOUNDxx.SND using PC-speaker, DAC-like, or direct-byte approximations."
    )
    parser.add_argument("path", type=Path, help="Path to SOUNDxx.SND")
    parser.add_argument(
        "--render-mode",
        choices=("dac", "speaker", "pcm"),
        default="speaker",
        help="`speaker` follows the PIT channel 2 mode-0 path; `dac` and `pcm` are fallback approximations",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=0,
        help="Playback/output sample rate; defaults to 8000 for `dac`/`pcm` and 44100 for `speaker`",
    )
    parser.add_argument(
        "--tick-rate",
        type=int,
        default=DEFAULT_SPEAKER_TICK_RATE,
        help="IRQ/timer rate for the speaker path; 8286 matches PIT divisor 0x48 and 16572 matches 0x24",
    )
    parser.add_argument(
        "--phase-param",
        type=lambda value: int(value, 0),
        default=DEFAULT_SPEAKER_PHASE_PARAM,
        help="Per-sound phase parameter from the opcode-9 table; the stream step is `0xFF - phase_param`",
    )
    parser.add_argument(
        "--xlat-kind",
        choices=("identity", "mode01", "mode23"),
        default=DEFAULT_SPEAKER_XLAT_KIND,
        help="Transfer-table shape before writing PIT counts; PC speaker uses `mode01`",
    )
    parser.add_argument(
        "--xlat-level",
        type=int,
        default=DEFAULT_SPEAKER_XLAT_LEVEL,
        help="Transfer-table level parameter; 72 matches the slower PC speaker timing path well",
    )
    parser.add_argument(
        "--lowpass-hz",
        type=float,
        default=DEFAULT_SPEAKER_LOWPASS_HZ,
        help="Low-pass filter cutoff for the speaker approximation",
    )
    args = parser.parse_args()
    play_snd(
        args.path,
        render_mode=args.render_mode,
        sample_rate=args.sample_rate,
        tick_rate=args.tick_rate,
        phase_param=args.phase_param,
        xlat_kind=args.xlat_kind,
        xlat_level=args.xlat_level,
        lowpass_hz=args.lowpass_hz,
    )


if __name__ == "__main__":
    main()
