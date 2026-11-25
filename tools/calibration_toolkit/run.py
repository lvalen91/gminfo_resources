#!/usr/bin/env python3
"""Single entry point for the calibration toolkit. Nothing to install.

    python3.14 run.py gui [file ...]  native macOS desktop UI (AppKit)
    python3 run.py web [--port N]     local web UI on http://127.0.0.1:5057/
    python3 run.py cli <command> ...  command line (python3 run.py cli --help)
    python3 run.py selftest           offline checks of the bundle and backend
"""
from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    mode, rest = argv[0], argv[1:]
    if mode == "gui":
        if sys.platform != "darwin":
            sys.exit("error: the desktop UI is macOS only; use the web or cli mode")
        sys.path.insert(2, str(ROOT / "vendor_mac"))  # bundled PyObjC (CPython 3.14)
        try:
            import gui
        except ImportError as e:
            sys.exit(f"error: the desktop UI needs Python 3.14, which the bundled PyObjC is built "
                     f"for, or a Python with PyObjC installed ({e})")
        gui.main(rest)
    elif mode == "web":
        if sys.version_info < (3, 10):
            sys.exit("error: the web UI needs Python 3.10 or newer")
        p = argparse.ArgumentParser(prog="run.py web")
        p.add_argument("--port", type=int, default=5057)
        args = p.parse_args(rest)
        from web.app import main as serve
        serve(args.port)
    elif mode == "cli":
        import cli
        sys.argv = ["caltool", *rest]
        cli.main()
    elif mode == "selftest":
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    else:
        print(f"error: unknown mode {mode!r}\n{__doc__}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
