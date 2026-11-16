import unittest
import tempfile
from pathlib import Path
from nova.brain.memory import NovaMemory

class TestNovaMemory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_memory.db"
        self.memory = NovaMemory(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_messages_flow(self):
        self.memory.add_message("session-1", "user", "Hello Nova")
        self.memory.add_message("session-1", "assistant", "Hello! How can I help?")

        messages = self.memory.get_recent_messages("session-1", limit=10)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "Hello Nova")
        self.assertEqual(messages[1]["role"], "assistant")

    def test_task_logging(self):
        self.memory.log_task("open_app", {"app_name": "Safari"}, "Opened Safari", status="success")
        history = self.memory.get_task_history(limit=5)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["tool_name"], "open_app")
        self.assertEqual(history[0]["status"], "success")

    def test_preferences(self):
        self.memory.set_preference("voice", "Samantha")
        self.assertEqual(self.memory.get_preference("voice"), "Samantha")
        self.assertEqual(self.memory.get_preference("non_existent", default=42), 42)

if __name__ == "__main__":
    unittest.main()
