"""Overlay plugins and update old status fixtures in a disposable core checkout.

The pinned core's exact-key assertions predate keep_running. Preserve its tests,
adding only the new key; use the plugin's ADS-B tests with realistic process waits.
Never run this against a development or deployed checkout.
"""
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def prepare(core):
    if not (core / 'src/plugins/runtime.py').is_file():
        raise ValueError('Expected a disposable Meshpoint compatibility checkout')
    shutil.copytree(ROOT / 'apps', core / 'apps', dirs_exist_ok=True)
    for name in ('acars', 'dab', 'p2000', 'pagers', 'pocsag', 'rtl433'):
        path = core / f'tests/optional/test_{name}_listener.py'
        text = path.read_text('utf-8')
        if '"keep_running"' not in text:
            text = text.replace('"running",', '"running", "keep_running",')
            path.write_text(text, 'utf-8')
    shutil.copyfile(ROOT / 'tests/test_adsb_listener.py',
                    core / 'tests/optional/test_adsb_listener.py')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.core.resolve())
