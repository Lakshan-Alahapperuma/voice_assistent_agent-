import unittest
from nova.tools.mac_tools import SetVolumeTool, GetSystemStatusTool
from nova.tools.shell_tools import RunCommandTool
from nova.tools.email_tools import DraftEmailTool

class TestMacAndShellTools(unittest.TestCase):
    def test_get_system_status(self):
        tool = GetSystemStatusTool()
        status = tool.execute()
        self.assertIn("disk", status)
        self.assertIn("total_gb", status["disk"])
        self.assertIn("macos_version", status)

    def test_shell_tool_allowlist_enforcement(self):
        tool = RunCommandTool()
        # Disallowed command
        res = tool.execute(command="rm -rf /")
        self.assertEqual(res["status"], "error")
        self.assertIn("not in Nova's allowlist", res["error"])

        # Allowed command (uptime)
        res_ok = tool.execute(command="uptime")
        self.assertEqual(res_ok["status"], "success")
        self.assertEqual(res_ok["exit_code"], 0)

    def test_draft_email_payload(self):
        tool = DraftEmailTool()
        # Open in mail app set to False to test in headless/sandbox environment
        res = tool.execute(recipient="manager@example.com", subject="Project Update", body="Completed tasks today.", open_in_mail_app=False)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["draft"]["recipient"], "manager@example.com")
        self.assertEqual(res["draft"]["subject"], "Project Update")

if __name__ == "__main__":
    unittest.main()
