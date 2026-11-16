import unittest
from nova.voice.wakeword import ContinuousWakeWordListener

class DummySTT:
    pass

class TestWakeWord(unittest.TestCase):
    def setUp(self):
        self.listener = ContinuousWakeWordListener(stt_engine=DummySTT())

    def test_extract_command_with_wake_word(self):
        detected, cmd = self.listener.extract_command("Hey Nova, open Safari and Notes")
        self.assertTrue(detected)
        self.assertEqual(cmd, "open Safari and Notes")

    def test_extract_command_variations(self):
        detected, cmd = self.listener.extract_command("Nova check my battery")
        self.assertTrue(detected)
        self.assertEqual(cmd, "check my battery")

        detected, cmd = self.listener.extract_command("Hi Nova, what is my disk space?")
        self.assertTrue(detected)
        self.assertEqual(cmd, "what is my disk space?")

    def test_just_wake_word(self):
        detected, cmd = self.listener.extract_command("Hey Nova")
        self.assertTrue(detected)
        self.assertEqual(cmd, "")

    def test_no_wake_word(self):
        detected, cmd = self.listener.extract_command("What time is it in Tokyo?")
        self.assertFalse(detected)
        self.assertEqual(cmd, "")

if __name__ == "__main__":
    unittest.main()
