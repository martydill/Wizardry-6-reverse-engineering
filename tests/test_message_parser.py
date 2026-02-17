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

        # Native runtime decode path should load all indexed IDs.
        self.assertEqual(718, len(messages))
        self.assertIn(100, messages)
        self.assertIn(10010, messages)
        self.assertIn(8200, messages)

        # Current decoder output is stage-1 tokenized text from MSG.DBS.
        self.assertIn("HUMAN", messages[100])
        self.assertIn("CHARRON", messages[8200])
        self.assertIn("RIVER STYX", messages[8200])
        self.assertIn("PROACHING THE GATE", messages[10010])
        self.assertGreater(len(messages[8200]), 200)

        self.assertIn(660, messages)
        self.assertIn("NEW CHARACTER", messages[660])

        print(f"Successfully loaded {len(messages)} messages.")
        print(f"ID 100: {messages[100]}")
        print(f"ID 8200: {messages[8200][:160]}")

    def test_readable_backend_improves_dialog(self):
        gamedata_dir = Path("gamedata")
        if not gamedata_dir.exists():
            self.skipTest("gamedata directory not found")

        messages = load_messages(gamedata_dir, backend="readable")
        self.assertIn(8200, messages)
        self.assertIn("YOU@", messages[8200])
        self.assertIn("CHARRON", messages[8200])
        self.assertIn("RIVER STYX", messages[8200])
        self.assertIn("QUESTION", messages[8200])
        self.assertIn(18950, messages)
        self.assertIn("* * * * * * *", messages[18950])
        self.assertIn("B O", messages[18950])
        self.assertIn(10030, messages)
        self.assertIn("ENTRANCE CHAMBER", messages[10030])
        self.assertIn("COAT OF DUST", messages[10030])
        self.assertIn("SCAMPERING NOISES ECHO", messages[10030])
        self.assertIn(12100, messages)
        self.assertIn("A SILENT, MYSTERIOUS DARK MAN APPEARS", messages[12100])
        self.assertIn("MAY I INTEREST YOU IN A BARGAIN?", messages[12100])
        self.assertIn(12560, messages)
        self.assertIn("THE REMAINS OF A LARGE WOODEN MACHINE", messages[12560])
        self.assertIn("MUCH LIKE A CATAPULT", messages[12560])

if __name__ == "__main__":
    unittest.main()
