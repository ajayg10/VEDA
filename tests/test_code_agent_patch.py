import tempfile
import unittest
from pathlib import Path

from core.code_agent.patch import UnifiedPatchApplier


class UnifiedPatchApplierTests(unittest.TestCase):
    def test_applies_valid_patches_to_existing_and_new_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.py").write_text("value = 1\n")
            patch = (
                "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-value = 1\n+value = 2\n"
                "--- /dev/null\n+++ b/new.py\n@@ -0,0 +1 @@\n+created = True\n"
            )

            changed = UnifiedPatchApplier().apply(str(root), patch)

            self.assertEqual((root / "app.py").read_text(), "value = 2\n")
            self.assertEqual((root / "new.py").read_text(), "created = True\n")

        self.assertEqual(changed, ["app.py", "new.py"])

    def test_rejects_patches_with_stale_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.py").write_text("value = 2\n")
            patch = "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-value = 1\n+value = 3\n"

            with self.assertRaises(ValueError):
                UnifiedPatchApplier().apply(str(root), patch)

            self.assertEqual((root / "app.py").read_text(), "value = 2\n")


if __name__ == "__main__":
    unittest.main()
