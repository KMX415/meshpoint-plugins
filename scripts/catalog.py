"""Deterministically build the official catalog from the shipped manifests."""
import argparse
import json
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def build_catalog(root=ROOT):
    plugins = []
    for folder in sorted((root / "apps").iterdir()):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        if folder.is_symlink():
            raise ValueError(f"Plugin directory must not be a symlink: {folder.name}")
        manifest = tomllib.loads((folder / "plugin.toml").read_text("utf-8"))
        if manifest["name"] != folder.name:
            raise ValueError(f"Plugin name does not match directory: {folder.name}")
        meta = manifest.get("meta", {})
        entry = {
            "id": folder.name, "kind": "app", "path": f"apps/{folder.name}",
            "version": manifest["version"], "meshpoint_api": manifest["meshpoint_api"],
            "provides": manifest["provides"], "description": meta.get("description", ""),
            "author": meta.get("author", ""), "homepage": meta.get("homepage", ""),
            # Reticulum uses the core's verified library recipe, not setup.sh.
            "has_setup": bool(manifest.get("deps", {}).get("setup")) or folder.name == "reticulum",
            "release_status": "experimental" if folder.name == "p25" else "release-candidate",
        }
        if manifest.get("hook"):
            entry["hook_host"] = manifest["hook"]["host"]
        if manifest.get("requires"):
            entry["requires"] = manifest["requires"]
        plugins.append(entry)
    return {"meshpoint_repo": 1, "name": "Meshpoint Official (release candidate)",
            "description": "Official optional plugins for Meshpoint v0.8.0 RC. Hardware validation varies by plugin; P25 is experimental.",
            "plugins": plugins, "themes": []}


def check_catalog(root=ROOT):
    actual = json.loads((root / "repo.json").read_text("utf-8"))
    expected = build_catalog(root)
    if actual != expected:
        raise ValueError("repo.json is stale; run python scripts/catalog.py --write")
    return expected


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        (ROOT / "repo.json").write_text(json.dumps(build_catalog(), indent=2) + "\n", "utf-8")
    else:
        check_catalog()
        print("Catalog matches all plugin manifests")
