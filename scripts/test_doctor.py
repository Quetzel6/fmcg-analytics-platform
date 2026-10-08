import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from importlib import metadata
from doctor import check_environment, REQUIRED_FILES


class EnvironmentTests(unittest.TestCase):
    def make_root(self, root):
        for name in REQUIRED_FILES:
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("fixture")

    def test_old_python_never_imports_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp, patch("doctor.importlib.import_module") as importer:
            result = check_environment(Path(tmp), version=(3, 10, 11))
            self.assertEqual(result["status"], "blocked")
            self.assertIn("Python 3.11", result["reason"])
            importer.assert_not_called()

    def test_collection_folder_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="project collection ") as tmp:
            result = check_environment(Path(tmp), version=(3, 13, 5))
            self.assertEqual(result["status"], "blocked")
            self.assertIn("scripts/run_release.py", result["reason"])

    def test_missing_dependency_reports_install_for_active_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.make_root(root)
            with patch("doctor.metadata.version", side_effect=metadata.PackageNotFoundError):
                result = check_environment(root, version=(3, 13, 5))
            self.assertEqual(result["status"], "blocked")
            self.assertIsNone(result["packages"]["numpy"]["installed"])
            self.assertIn("requirements.txt", result["install_command"])

    def test_mismatched_pin_does_not_import_that_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.make_root(root)
            with patch("doctor.metadata.version", return_value="wrong"), patch("doctor.importlib.import_module") as importer:
                result = check_environment(root, version=(3, 13, 5))
            self.assertEqual(result["status"], "blocked")
            self.assertIn("numpy must be 2.3.5", result["reason"])
            importer.assert_not_called()

    def test_broken_binary_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.make_root(root)
            with patch("doctor.metadata.version", side_effect=["2.3.5", "3.2.10"]), patch("doctor.importlib.import_module", side_effect=ImportError):
                result = check_environment(root, version=(3, 13, 5))
            self.assertEqual(result["status"], "blocked")
            self.assertIn("cannot be imported", result["reason"])

    def test_valid_environment_is_read_only_and_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.make_root(root)
            with patch("doctor.metadata.version", side_effect=["2.3.5", "3.2.10"]), patch("doctor.importlib.import_module"):
                result = check_environment(root, version=(3, 13, 5))
            self.assertEqual(result["status"], "ready")
            self.assertFalse((root / "output").exists())
            self.assertEqual(len(result["packages"]), 2)


if __name__ == "__main__":
    unittest.main()
