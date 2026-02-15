import struct
from bane.data.message_parser import load_messages

def test():
    messages = load_messages('gamedata')
    print("Original ID 100: " + messages[100])
    print("Cleaned ID 100:  " + messages[100].replace('E', ' '))
    print("\nOriginal ID 450: " + messages[450])
    print("Cleaned ID 450:  " + messages[450].replace('E', ' '))
    print("\nOriginal ID 200: " + messages[200])
    print("Cleaned ID 200:  " + messages[200].replace('E', ' '))

if __name__ == "__main__":
    test()