# `SOUNDxx.SND` File Format

## Summary

`SOUNDxx.SND` is not raw PCM. It is a small resource-chunk container used by Wizardry 6 / Bane of the Cosmic Forge.

The file stores either:

- a raw byte stream, or
- a byte stream compressed with a tree-based bit decoder

After decoding, the payload is still not self-describing audio PCM. The game feeds the decoded bytes into hardware-specific playback code, using additional per-sound metadata loaded from `SCENARIO.DBS`.

## Provenance

This format description is based on disassembly of:

- `WMAZE.OVR:0x9948..0x9A23`
- `WROOT.EXE:0x33E9..0x3556`
- `WROOT.EXE:0x1462..0x1A46`

Relevant local references:

- [SOUND_PLAYBACK_RE.md](../docs/SOUND_PLAYBACK_RE.md)
- [decode_snd.py](../scratch/decode_snd.py)

## Container Layout

All multibyte integers are little-endian.

### Case 1: Uncompressed

If the first word is `0x0000`, the remainder of the file is the decoded byte stream.

```text
+0x00  u16  tree_len = 0
+0x02  u8[] decoded bytes
```

### Case 2: Compressed

If the first word is nonzero, it is the decode-tree size in bytes.

```text
+0x00  u16  tree_len
+0x02  u8[tree_len] decode tree
+0x02+tree_len  u16  output_len
+0x04+tree_len  u8[] bitstream
```

Constraints inferred from the loader:

- `tree_len > 0`
- the decode tree is addressed as 16-bit entries
- the decoded output length is stored explicitly as `output_len`

## Decode Tree Encoding

The tree is a flat array of 16-bit signed values.

Traversal begins at byte offset `0` within the tree. Each node occupies two child entries:

- left child at `node_offset + 0`
- right child at `node_offset + 2`

Each child entry is interpreted as a signed 16-bit value:

- `>= 0`: leaf node; the value is the decoded output byte
- `< 0`: internal node; the next node offset is `(-value) << 2`

That `<< 2` matters: internal-node references are effectively stored as node indices, not raw byte offsets.

## Bitstream Semantics

The compressed payload begins with:

- `u16 output_len`
- the first compressed data byte

Bits are consumed MSB-first from each compressed byte.

For each decoded output byte:

1. Start at tree node offset `0`.
2. Consume one bit.
3. Use bit `0` for the left child, bit `1` for the right child.
4. If the selected child is a leaf, emit that byte.
5. If the selected child is internal, jump to the referenced node and continue with the next bit.
6. Stop after emitting exactly `output_len` bytes.

The original decoder refills the compressed-byte register whenever its local bit counter reaches zero. The implementation in [decode_snd.py](/C:/Users/marty/Documents/code/bane/scratch/decode_snd.py) mirrors that logic directly.

## Reference Decoder Pseudocode

```python
def decode_snd(data: bytes) -> bytes:
    tree_len = u16le(data, 0)
    if tree_len == 0:
        return data[2:]

    tree = data[2 : 2 + tree_len]
    stream = data[2 + tree_len :]
    output_len = u16le(stream, 0)

    si = 2
    current = stream[si]
    si += 1
    bit_count = 8
    out = bytearray()

    while len(out) < output_len:
        node = 0
        cx = bit_count

        while True:
            bit = 1 if (current & 0x80) else 0
            current = (current << 1) & 0xFF
            edge = node + (2 if bit else 0)
            child = s16le(tree, edge)

            if child >= 0:
                node = child
                break

            node = (-child) << 2
            cx -= 1
            if cx == 0:
                cx = 8
                current = stream[si]
                si += 1

        bit_count = cx - 1
        if bit_count < 0:
            bit_count = 8
            current = stream[si]
            si += 1

        out.append(node & 0xFF)

        if bit_count == 0 and len(out) < output_len:
            bit_count = 8
            current = stream[si]
            si += 1

    return bytes(out)
```

## What The Decoded Bytes Represent

The decoded bytes are playback control data, not portable PCM samples.

The game’s runtime path is:

1. load and decode `SOUNDxx.SND`
2. load separate per-sound playback parameters from the opcode-9 table in `SCENARIO.DBS`
3. build a 256-byte transfer table
4. install an IRQ0 handler
5. feed decoded bytes through that table into the selected audio device path

Observed output families in `WROOT.EXE`:

- PC speaker / PIT channel 2 path
- AdLib-like port `0x389` path
- another device path using a base port stored at `cs:0x175B`

So the `.SND` file format only explains how to get the decoded byte stream. It does not, by itself, define an exact waveform.

## External Playback Metadata

Exact playback depends on metadata outside the `.SND` file.

For the opcode-9 per-sound records reconstructed from `MASTER.HDR`, `DISK.HDR`, and `SCENARIO.DBS`, the relevant fields are:

```text
+0x00  u16  unused here
+0x02  u16  unused here
+0x04  u16  caller parameter / related offset
+0x06  u16  unused here
+0x08  u16  phase parameter
+0x0A  u8   transfer-table level
+0x0B  u8   device/mode selector high-byte source
```

Fields actually confirmed by playback disassembly:

- `word +0x08` low byte influences decoded-stream advance rate
- `byte +0x0A` is used to build the transfer table
- `byte +0x0B` contributes to the hardware path selection passed into `WROOT:0x1462`

Example for `SOUND00.SND`:

- phase parameter: `0x007E`
- transfer-table level: `0x49`
- mode byte: `0x01`

## PC Speaker Playback Notes

For the PC speaker path, the decoded bytes are translated through the transfer table and then written as PIT channel-2 reload values in mode `0`.

Important consequences:

- the stream advance step is not fixed
- the effective decoded-byte rate depends on both PIT IRQ rate and the per-sound phase parameter
- the sound is closer to timer-driven pulse-width control than direct PCM output

For `SOUND00.SND`, the per-sound step derived from the metadata is based on `0xFF - 0x7E = 0x81` on the slow path.

## Practical Decoder Rule

If you only want the decoded payload:

- read `u16 tree_len`
- if `tree_len == 0`, return `data[2:]`
- otherwise decode the tree/bitstream until `output_len` bytes are produced

If you want accurate playback:

- decoding `SOUNDxx.SND` is necessary but not sufficient
- you must also reproduce the game’s runtime metadata and hardware path

## Known Limitations

These points are still partly inferred rather than fully proven:

- the exact semantic labels for every opcode-9 field beyond the confirmed playback uses
- the exact mapping between every mode byte and every supported sound device
- the exact analog response of the original PC speaker hardware

Those gaps do not affect the core on-disk `.SND` decode format described above.
