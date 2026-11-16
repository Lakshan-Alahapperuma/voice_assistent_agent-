import unittest
import tempfile
import shutil
from pathlib import Path
from nova.tools.file_tools import ReadFileTool, WriteFileTool, OrganizeFolderTool, SearchFilesTool

class TestFileTools(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_write_and_read_file(self):
        writer = WriteFileTool()
        reader = ReadFileTool()

        target_file = self.base_path / "hello.txt"
        content = "Hello, Nova assistant!"

        # Write
        res_write = writer.execute(filepath=str(target_file), content=content)
        self.assertEqual(res_write["status"], "success")
        self.assertTrue(target_file.exists())

        # Read
        res_read = reader.execute(filepath=str(target_file))
        self.assertEqual(res_read["content"], content)

    def test_backup_on_overwrite(self):
        writer = WriteFileTool()
        target_file = self.base_path / "important.txt"

        writer.execute(filepath=str(target_file), content="Original content")
        res_update = writer.execute(filepath=str(target_file), content="New modified content")

        self.assertIsNotNone(res_update["backup_created"])
        backup_file = Path(res_update["backup_created"])
        self.assertTrue(backup_file.exists())
        self.assertEqual(backup_file.read_text(encoding="utf-8"), "Original content")

    def test_organize_folder_preview_and_run(self):
        folder = self.base_path / "Downloads"
        folder.mkdir()

        (folder / "document.pdf").write_text("dummy pdf")
        (folder / "photo.png").write_text("dummy png")
        (folder / "script.py").write_text("print(1)")

        organizer = OrganizeFolderTool()

        # Preview (dry run)
        preview = organizer.execute(folder_path=str(folder), dry_run=True)
        self.assertEqual(preview["status"], "preview")
        self.assertEqual(preview["total_files"], 3)
        self.assertTrue((folder / "document.pdf").exists())

        # Real run
        run_res = organizer.execute(folder_path=str(folder), dry_run=False)
        self.assertEqual(run_res["status"], "success")
        self.assertEqual(run_res["total_organized"], 3)
        self.assertTrue((folder / "Documents" / "document.pdf").exists())
        self.assertTrue((folder / "Images" / "photo.png").exists())
        self.assertTrue((folder / "Code" / "script.py").exists())

if __name__ == "__main__":
    unittest.main()
