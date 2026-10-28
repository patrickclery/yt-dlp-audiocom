"""Run AudioComIE._TESTS through yt-dlp's own test/test_download.py harness.

Usage: python scripts/run_live_tests.py <harness-root> [pytest -k expr] [extra pytest args]

<harness-root> must hold test/test_download.py from the SAME yt-dlp version as the
interpreter running this script, and no yt_dlp/ directory: test_download.py puts
<harness-root> first on sys.path, so a full clone would shadow the installed yt-dlp.
The -k expression defaults to AudioCom. Exits with pytest's return code (5 when no
test was collected). Network required; run it from a writable throwaway directory.
"""
import os
import sys

import pytest
from yt_dlp.plugins import load_all_plugins


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    harness = argv[1]
    if os.path.isdir(os.path.join(harness, 'yt_dlp')):
        sys.exit(f'{harness} contains yt_dlp/; use a test-only (sparse) checkout')
    target = os.path.join(harness, 'test', 'test_download.py')
    if not os.path.isfile(target):
        sys.exit(f'{target} not found')
    # test_download.py builds its test methods from gen_extractors() at import time,
    # so plugin extractors must be registered before pytest imports it.
    load_all_plugins()
    return pytest.main([
        target, '-p', 'no:cacheprovider',
        '-k', argv[2] if len(argv) > 2 else 'AudioCom', *argv[3:]])


if __name__ == '__main__':
    sys.exit(main(sys.argv))
