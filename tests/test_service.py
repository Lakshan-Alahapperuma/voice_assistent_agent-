import unittest
from nova.ui.service import get_service_paths, is_service_installed

class TestService(unittest.TestCase):
    def test_service_paths(self):
        paths = get_service_paths()
        self.assertIn("python", paths)
        self.assertIn("main", paths)
        self.assertIn("stdout", paths)
        self.assertTrue(str(paths["main"]).endswith("main.py"))

    def test_is_service_installed(self):
        # Should return a boolean
        res = is_service_installed()
        self.assertIsInstance(res, bool)

if __name__ == "__main__":
    unittest.main()
