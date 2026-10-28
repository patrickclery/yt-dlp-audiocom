"""Plugin packaging and discovery.

test_plugin_listed needs the project installed into the interpreter running
pytest (`pip install -e .`, alongside yt-dlp and pytest) so the `yt-dlp` console
script can discover the plugin with PYTHONPATH removed. It is skipped otherwise.
"""
import importlib.metadata
import os
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN_PKG = ROOT / 'yt_dlp_plugins'
PLUGIN_FILE = PLUGIN_PKG / 'extractor' / 'audiocom.py'


def test_layout():
    # Namespace package: an __init__.py here would break merging with other
    # plugin packages (e.g. MeTube's rumble_fix.py) in yt_dlp_plugins.extractor.
    assert not (PLUGIN_PKG / '__init__.py').exists()
    assert not (PLUGIN_PKG / 'extractor' / '__init__.py').exists()
    for line in PLUGIN_FILE.read_text(encoding='utf-8').splitlines():
        assert not line.startswith('from .'), f'relative import: {line}'


def test_plugin_listed():
    ytdlp = next((p for p in (pathlib.Path(sys.executable).with_name(n) for n in ('yt-dlp', 'yt-dlp.exe'))
                  if p.is_file()), None)
    if ytdlp is None:
        pytest.skip('no yt-dlp console script next to the running interpreter')
    try:
        importlib.metadata.distribution('yt-dlp-audiocom')
    except importlib.metadata.PackageNotFoundError:
        pytest.skip('yt-dlp-audiocom is not installed; run `pip install -e .` first')
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    proc = subprocess.run(
        [str(ytdlp), '-v', '--ignore-config'],
        cwd='/', env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=120)
    # yt-dlp exits non-zero without a URL; only the debug output matters.
    # yt-dlp sorts and joins plugin names, so AudioComIE need not come first.
    assert re.search(r'Extractor Plugins: .*\bAudioComIE\b', proc.stdout), proc.stdout
    # Plugin import errors are swallowed by yt-dlp and only printed.
    assert 'Error while importing' not in proc.stdout, proc.stdout
