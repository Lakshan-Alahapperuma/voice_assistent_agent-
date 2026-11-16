import unittest
from nova.tools.mac_tools import OpenUrlTool, SearchWebTool, PlayMusicTool, MediaControlTool

class TestMediaAndWebTools(unittest.TestCase):
    def test_open_url_schema(self):
        tool = OpenUrlTool()
        self.assertEqual(tool.name, "open_url")
        self.assertIn("url", tool.parameters["properties"])

    def test_search_web_payload(self):
        tool = SearchWebTool()
        self.assertEqual(tool.name, "search_web")
        self.assertIn("query", tool.parameters["properties"])
        self.assertIn("engine", tool.parameters["properties"])

    def test_play_music_tool(self):
        tool = PlayMusicTool()
        self.assertEqual(tool.name, "play_music")
        self.assertIn("query", tool.parameters["properties"])
        self.assertIn("platform", tool.parameters["properties"])

    def test_media_control_tool(self):
        tool = MediaControlTool()
        self.assertEqual(tool.name, "media_control")
        self.assertIn("action", tool.parameters["properties"])

if __name__ == "__main__":
    unittest.main()
