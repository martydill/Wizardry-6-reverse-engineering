from __future__ import annotations

import argparse
import wave
from pathlib import Path


def decode_snd(path: Path) -> bytes:
    data = path.read_bytes()
    if len(data) < 4:
        raise ValueError(f"{path} is too small to be a valid SND resource")

    tree_len = int.from_bytes(data[0:2], "little")
    if tree_len == 0:
        return data[2:]

    if len(data) < 2 + tree_len + 3:
        raise ValueError(f"{path} is truncated")

    tree = data[2 : 2 + tree_len]
    stream = data[2 + tree_len :]
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

            if edge + 2 > len(tree):
                raise ValueError(f"{path} decode tree overran at offset 0x{edge:X}")

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


def write_wav(path: Path, pcm_u8: bytes, sample_rate: int) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(1)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_u8)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Decode Wizardry 6/Bane of the Cosmic Forge SOUNDxx.SND resources "
            "using the WROOT:0x33E9 chunk decompressor."
        )
    )
    parser.add_argument("input", type=Path, help="Path to SOUNDxx.SND")
    parser.add_argument(
        "--raw-out",
        type=Path,
        help="Write the decoded byte stream to a raw .bin file",
    )
    parser.add_argument(
        "--wav-out",
        type=Path,
        help="Write the decoded byte stream as unsigned 8-bit mono WAV",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=8286,
        help="Sample rate for WAV export; 8286 and 16572 are the two likely runtime rates",
    )
    args = parser.parse_args()

    decoded = decode_snd(args.input)
    print(
        f"{args.input.name}: decoded {len(decoded)} bytes, "
        f"min={min(decoded)}, max={max(decoded)}, unique={len(set(decoded))}"
    )

    if args.raw_out:
        args.raw_out.write_bytes(decoded)
        print(f"wrote raw output to {args.raw_out}")

    if args.wav_out:
        write_wav(args.wav_out, decoded, args.sample_rate)
        print(f"wrote wav output to {args.wav_out} at {args.sample_rate} Hz")


if __name__ == "__main__":
    main()
