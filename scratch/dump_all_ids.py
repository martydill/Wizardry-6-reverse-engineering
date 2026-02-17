from bane.data.message_parser import MessageParser


def dump() -> None:
    parser = MessageParser("gamedata/MISC.HDR")
    messages = parser.load(
        "gamedata/MSG.DBS",
        "gamedata/MSG.HDR",
        backend="readable",
    )

    ids = sorted(messages.keys())
    print(f"Total IDs: {len(ids)}\n")
    for msg_id in ids:
        print(f"ID {msg_id}: {messages[msg_id]}\n")


if __name__ == "__main__":
    dump()
