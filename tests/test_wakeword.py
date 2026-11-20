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

    def test_is_dismissal(self):
        self.assertTrue(self.listener.is_dismissal("thank you"))
        self.assertTrue(self.listener.is_dismissal("Thank you!"))
        self.assertTrue(self.listener.is_dismissal("thanks"))
        self.assertTrue(self.listener.is_dismissal("bye"))
        self.assertTrue(self.listener.is_dismissal("go to sleep"))
        self.assertTrue(self.listener.is_dismissal("that's all"))
        self.assertTrue(self.listener.is_dismissal("never mind"))
        self.assertFalse(self.listener.is_dismissal("open Safari"))
        self.assertFalse(self.listener.is_dismissal("what is the weather"))

    def test_conversation_state_and_timeout(self):
        self.assertFalse(self.listener.conversation_active)
        self.listener.conversation_active = True
        self.listener.last_activity_time = 100.0
        self.listener.conversation_timeout = 8.0

        # Within timeout
        self.assertTrue(105.0 - self.listener.last_activity_time <= self.listener.conversation_timeout)
        # Exceeded timeout
        self.assertFalse(110.0 - self.listener.last_activity_time <= self.listener.conversation_timeout)

if __name__ == "__main__":
    unittest.main()
