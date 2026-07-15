import tempfile
import unittest
from pathlib import Path

from core.project.scanner import ProjectScanner


class ProjectScannerTests(unittest.TestCase):
    def test_detects_docker_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "services").mkdir()
            (root / "services" / "Dockerfile").touch()

            info = ProjectScanner().scan(str(root))

        self.assertTrue(info.uses_docker)

    def test_detects_ci_providers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflow_dir = root / ".github" / "workflows"
            workflow_dir.mkdir(parents=True)
            (workflow_dir / "test.yml").touch()
            (root / ".gitlab-ci.yml").touch()

            info = ProjectScanner().scan(str(root))

        self.assertCountEqual(info.ci_providers, ["GitHub Actions", "GitLab CI"])

    def test_detects_distinct_package_managers_from_lockfiles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package-lock.json").touch()
            (root / "yarn.lock").touch()
            (root / "requirements.txt").touch()
            (root / "nested").mkdir()
            (root / "nested" / "pnpm-lock.yaml").touch()

            info = ProjectScanner().scan(str(root))

        self.assertCountEqual(info.package_managers, ["npm", "Yarn", "pip", "pnpm"])

    def test_does_not_report_a_package_manager_without_known_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.py").touch()

            info = ProjectScanner().scan(str(root))

        self.assertEqual(info.package_managers, [])


if __name__ == "__main__":
    unittest.main()
