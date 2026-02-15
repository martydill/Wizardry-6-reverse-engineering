import unittest
from pathlib import Path
from bane.data.message_parser import load_messages

class TestMessageParser(unittest.TestCase):
    def test_load_msg_dbs(self):
        # This test expects gamedata to be present in the project root
        gamedata_dir = Path("gamedata")
        if not gamedata_dir.exists():
            self.skipTest("gamedata directory not found")
            
        messages = load_messages(gamedata_dir)
        
        # Verify some known message IDs from MSG.HDR analysis
        self.assertIn(100, messages)
        self.assertIn("HUMAN", messages[100])
        
        self.assertIn(660, messages)
        self.assertIn("HUMAN", messages[660])
        self.assertIn("CANCEL", messages[660])
        
        # Check for another ID from the output
        self.assertIn(450, messages)
        self.assertIn("TRADE HOW MANY", messages[450])
        
        print(f"Successfully loaded {len(messages)} messages.")
        print(f"ID 100: {messages[100]}")
        print(f"ID 450: {messages[450]}")

if __name__ == "__main__":
    unittest.main()