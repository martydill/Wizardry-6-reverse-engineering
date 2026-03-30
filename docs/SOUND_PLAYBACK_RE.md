# Sound Playback Reverse Engineering

`gamedata/SOUNDxx.SND` is not raw 16-bit PCM.

The original game uses a two-stage path:

1. `WMAZE.OVR:0x9948..0x9A23` builds `SOUNDxx.SND`, opens it, and calls `WROOT:0x33E9` with slot `0x0E`.
2. `WROOT:0x33E9..0x3556` loads the file into the runtime slot table at `cs:0x3579 + 4 * slot`.

## On-disk format

`WROOT:0x33E9` shows that `.SND` files are compressed resource chunks.

- If the first word is `0`, the rest of the file is stored raw.
- Otherwise:
  - word `0x0000`: decode-tree byte length
  - next `tree_len` bytes: binary decode tree
  - next word in the following stream: decoded output length
  - remaining bytes: bitstream decoded by `WROOT:0x34BC..0x3555`

That decode tree stores:

- non-negative child words: literal byte values
- negative child words: internal-node references, with the next node at `(-word) << 2`

I mirrored that logic in [decode_snd.py](/C:/Users/marty/Documents/code/bane/scratch/decode_snd.py).

## What the decoded bytes are

After decompression, the payload is byte-oriented, not 16-bit samples.

Relevant playback code is `WROOT.EXE:0x1462..0x19BF`:

- `0x1462` installs/restores IRQ0 handlers and programs PIT/PIC state.
- `0x17FE..0x1887` builds a 256-byte transfer table at `cs:0x1A4B`.
- `0x16B0..0x16D7` patches the IRQ handlers with a per-sound phase increment and end pointer.
- `0x18C3`, `0x1901`, `0x1919`, and `0x1969` are IRQ handlers that:
  - read one byte from the decoded sound stream
  - translate it through the 256-byte table via `XLAT`
  - write the translated value to either:
    - AdLib data port `0x389`, or
    - a port stored in `cs:0x175B`, or
    - PIT channel programming for speaker-style output

The stream advance is not fixed. `0x16B0..0x16D7` computes `step = 0xFF - word_+8_lowbyte`, optionally halves it on the fast timing path, and patches that immediate into the handlers:

- `0x18DD`, `0x190E`, `0x1935`, `0x1956`, `0x197D`, `0x19F7`, `0x1A28`

For `SOUND00.SND`, the opcode-9 bootstrap record supplies:

- phase parameter `0x7E`, so the slow-path accumulator step is `0x81`
- transfer-table level `0x49`

## Effective sample rate

`WROOT:0x1651..0x1668` programs PIT channel 0 with divisor `0x24` or `0x48`.

That implies two IRQ rates:

- `1193180 / 0x24 ~= 33144 Hz`
- `1193180 / 0x48 ~= 16572 Hz`

The actual decoded-byte consumption rate depends on the patched step. For `SOUND00.SND` it is approximately:

- fast path: `33144 * 0x40 / 256 ~= 8286 bytes/s`
- slow path: `16572 * 0x81 / 256 ~= 8350.55 bytes/s`

So the decoded payload is a timer-driven control stream whose effective byte rate depends on both the PIT divisor and the per-sound phase parameter, not a fixed-rate PCM stream.

## Why `loaders/sound_player.py` sounds like static

That loader is wrong in two independent ways:

- it feeds the compressed on-disk `.SND` bytes directly to the mixer
- it interprets them as signed 16-bit mono PCM

The original path is:

1. decompress resource chunk
2. treat decoded payload as a byte stream
3. map bytes through a hardware-specific 256-entry table
4. output through timer-driven IRQ playback to AdLib / speaker-related hardware

## Practical next step

To audition the decoded stream directly on a modern machine, the best approximation is:

- decompress with [decode_snd.py](/C:/Users/marty/Documents/code/bane/scratch/decode_snd.py)
- try unsigned 8-bit mono WAV at `8286` Hz first
- if timing feels too slow, try `16572` Hz
