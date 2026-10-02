import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("catalog", Path(__file__).resolve().parents[1] / "scripts/catalog.py")
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


class CatalogTests(unittest.TestCase):
    def test_python_cache_is_not_a_plugin(self):
        (self.root / 'apps/__pycache__').mkdir()
        self.assertEqual(len(catalog.build_catalog(self.root)['plugins']), 1)

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "apps/demo").mkdir(parents=True)
        self.manifest = self.root / "apps/demo/plugin.toml"
        self.manifest.write_text('name="demo"\nversion="1.0"\nmeshpoint_api=1\nprovides=["sidebar"]\n', "utf-8")

    def write_catalog(self):
        (self.root / "repo.json").write_text(json.dumps(catalog.build_catalog(self.root)), "utf-8")

    def test_name_cannot_redirect_installation(self):
        self.manifest.write_text(self.manifest.read_text().replace('name="demo"', 'name="different"'))
        with self.assertRaises(ValueError):
            catalog.build_catalog(self.root)

    def test_changed_version_requires_catalog_refresh(self):
        self.write_catalog()
        self.manifest.write_text(self.manifest.read_text().replace('version="1.0"', 'version="2.0"'))
        with self.assertRaises(ValueError):
            catalog.check_catalog(self.root)

    def test_catalog_cannot_redirect_to_another_path(self):
        self.write_catalog()
        path = self.root / "repo.json"
        data = json.loads(path.read_text())
        data["plugins"][0]["path"] = "../outside"
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            catalog.check_catalog(self.root)

    def test_new_plugin_cannot_be_omitted(self):
        self.write_catalog()
        other = self.root / "apps/other"
        other.mkdir()
        (other / "plugin.toml").write_text(self.manifest.read_text().replace('name="demo"', 'name="other"'))
        with self.assertRaises(ValueError):
            catalog.check_catalog(self.root)

    def test_dependency_is_carried_into_catalog(self):
        self.manifest.write_text(self.manifest.read_text() + 'requires="host"\n')
        self.assertEqual(catalog.build_catalog(self.root)["plugins"][0]["requires"], "host")


if __name__ == "__main__":
    unittest.main()
