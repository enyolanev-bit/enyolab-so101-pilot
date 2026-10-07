"""Bridge painter shortcut: the Golden Gate bridge WITHOUT Astra, same safe pipeline as run_boris.py.

    python bridge_painter.py --dry-run     checks + cameras + plan, no torque, no motion
    python bridge_painter.py --go          same, then asks you to type GO and draws

Drawing logic lives in painter.py (template "golden_gate_bridge"); execution in run_boris.py.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_boris  # noqa: E402

if __name__ == "__main__":
    if sys.argv[1:] not in (["--dry-run"], ["--go"]):
        sys.exit("usage: bridge_painter.py --dry-run | --go")
    sys.argv = [sys.argv[0], "draw a simple Golden Gate Bridge", "--offline-astra"] + \
        (["--dry-run"] if sys.argv[1] == "--dry-run" else [])
    sys.exit(run_boris.main())
