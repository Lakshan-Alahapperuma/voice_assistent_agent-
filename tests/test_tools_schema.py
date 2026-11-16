import unittest
from nova.tools import create_default_registry

class TestToolsSchema(unittest.TestCase):
    def test_registry_and_schema_generation(self):
        registry = create_default_registry()
        tools = registry.list_tools()

        self.assertGreaterEqual(len(tools), 8)

        ollama_tools = registry.get_ollama_tools()
        self.assertEqual(len(ollama_tools), len(tools))

        for t in ollama_tools:
            self.assertEqual(t["type"], "function")
            fn = t["function"]
            self.assertIn("name", fn)
            self.assertIn("description", fn)
            self.assertIn("parameters", fn)
            self.assertEqual(fn["parameters"]["type"], "object")

    def test_confirmation_flags(self):
        registry = create_default_registry()

        write_tool = registry.get_tool("write_file")
        self.assertTrue(write_tool.requires_confirmation)

        send_email_tool = registry.get_tool("send_email")
        self.assertTrue(send_email_tool.requires_confirmation)

        run_cmd_tool = registry.get_tool("run_command")
        self.assertTrue(run_cmd_tool.requires_confirmation)

        read_tool = registry.get_tool("read_file")
        self.assertFalse(read_tool.requires_confirmation)

if __name__ == "__main__":
    unittest.main()
