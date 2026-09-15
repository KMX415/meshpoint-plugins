"""Check the catalog with the target Meshpoint runtime, without starting plugins."""
import argparse
from pathlib import Path
import subprocess
import sys

from catalog import ROOT, check_catalog


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--core", type=Path, required=True)
    args = parser.parse_args()
    core = args.core.resolve()
    if not (core / "src/plugins/installer.py").is_file():
        parser.error("--core must point to a Meshpoint checkout")
    sys.path.insert(0, str(core))
    from src.plugins.installer import validate_staged_app
    from src.plugins.sources import parse_catalog
    from src.plugins.runtime import SUPPORTED_CAPABILITIES

    catalog = check_catalog()
    parsed = parse_catalog((ROOT / "repo.json").read_bytes())
    assert len(parsed["plugins"]) == len(catalog["plugins"])
    manifests = {}
    for entry in catalog["plugins"]:
        folder = ROOT / entry["path"]
        manifest = validate_staged_app(folder)
        unsupported = set(manifest.provides) - SUPPORTED_CAPABILITIES
        if unsupported:
            raise ValueError(f"Unsupported capabilities in {manifest.name}: {unsupported}")
        manifests[manifest.name] = manifest
        for file in folder.rglob("*"):
            if file.is_symlink():
                raise ValueError(f"Symlinks cannot be installed: {file}")
            if file.suffix == ".py":
                compile(file.read_bytes(), str(file), "exec")
            elif file.suffix == ".js":
                subprocess.run(["node", "--check", str(file)], check=True)
    for name, manifest in manifests.items():
        seen = {name}
        while manifest.requires or manifest.hook:
            target = manifest.requires
            if manifest.hook:
                target = next((key for key, value in manifests.items()
                               if value.sidebar and value.sidebar.route == manifest.hook.host), None)
            if target not in manifests or target in seen:
                raise ValueError(f"Missing or cyclic dependency in {name}")
            seen.add(target)
            manifest = manifests[target]
    print(f"Validated {len(manifests)} installable plugins against {core}")


if __name__ == "__main__":
    main()
