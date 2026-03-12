#!/usr/bin/env python3
"""
Wizardry 6: Bane of the Cosmic Forge — Message Decoder
=======================================================
Decodes MSG.DBS / MSG.HDR using the Huffman tree in MISC.HDR.

Usage:
    # Print all messages
    python -m loaders.message_parser

    # Print a specific message by ID
    python -m loaders.message_parser 10010

    # Search for text in messages
    python -m loaders.message_parser --search "gate"

    # Save all messages to a file
    python -m loaders.message_parser --output all_messages.txt

    # Show raw control codes instead of interpreting them
    python -m loaders.message_parser --raw
"""

import argparse
from pathlib import Path

from bane.data.message_parser import load_messages

GAMEDATA_DIR = Path("gamedata")


def main() -> None:
    parser = argparse.ArgumentParser(description="Decode Wizardry 6 messages from MSG.DBS")
    parser.add_argument(
        "id",
        nargs="?",
        type=int,
        help="Message ID to display (omit to show all)",
    )
    parser.add_argument(
        "--search", "-s",
        metavar="TEXT",
        help="Search for messages containing TEXT (case-insensitive)",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="Save output to FILE instead of printing",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Show raw control codes instead of interpreting them",
    )
    args = parser.parse_args()

    backend = "raw" if args.raw else "readable"
    msgs = load_messages(GAMEDATA_DIR, backend=backend)

    # Filter messages
    if args.id is not None:
        if args.id not in msgs:
            print(f"Message ID {args.id} not found.")
            return
        selected = {args.id: msgs[args.id]}
    elif args.search:
        needle = args.search.lower()
        selected = {mid: text for mid, text in msgs.items() if needle in text.lower()}
        if not selected:
            print(f"No messages found containing '{args.search}'.")
            return
    else:
        selected = msgs

    # Format output
    lines = []
    for mid in sorted(selected):
        lines.append(f"=== Message ID {mid} ===")
        lines.append(selected[mid])
        lines.append("")

    output = "\n".join(lines)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Saved {len(selected)} message(s) to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
