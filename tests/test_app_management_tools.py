import unittest
from nova.tools.mac_tools import CloseAppTool, SwitchAppTool, ListRunningAppsTool

class TestAppManagementTools(unittest.TestCase):
    def test_close_app_schema(self):
        tool = CloseAppTool()
        self.assertEqual(tool.name, "close_app")
        self.assertIn("app_name", tool.parameters["properties"])
        self.assertIn("force", tool.parameters["properties"])

    def test_switch_app_schema(self):
        tool = SwitchAppTool()
        self.assertEqual(tool.name, "switch_app")
        self.assertIn("app_name", tool.parameters["properties"])

    def test_list_running_apps_schema(self):
        tool = ListRunningAppsTool()
        self.assertEqual(tool.name, "list_running_apps")

if __name__ == "__main__":
    unittest.main()
