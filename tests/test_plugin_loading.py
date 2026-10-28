import os
import pathlib
import subprocess
import sys

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
    ytdlp = pathlib.Path(sys.executable).with_name('yt-dlp')
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    proc = subprocess.run(
        [str(ytdlp), '-v', '--ignore-config'],
        cwd='/', env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=120)
    # yt-dlp exits non-zero without a URL; only the debug output matters.
    assert 'Extractor Plugins: AudioComIE' in proc.stdout, proc.stdout
    # Plugin import errors are swallowed by yt-dlp and only printed.
    assert 'Error while importing' not in proc.stdout, proc.stdout
