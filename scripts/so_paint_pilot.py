"""UNSUPPORTED / EXPERIMENTAL — not part of the Boris handoff.

Entry point to a separate `so-paint` checkout (observation/simulation only) that is NOT included in this
repository. It refuses to run unless SO_PAINT_REPO explicitly points to that checkout: it never guesses a
sibling directory, so nothing is executed from an unexpected folder next to a clone.

    SO_PAINT_REPO=/path/to/so-paint python scripts/so_paint_pilot.py doctor|observe|simulate-bridge
"""

import argparse
import datetime
import os
import pathlib
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["doctor", "observe", "simulate-bridge"])
    args = parser.parse_args()
    raw = os.environ.get("SO_PAINT_REPO", "").strip()
    if not raw:
        sys.exit("UNSUPPORTED: scripts/so_paint_pilot.py needs a separate so-paint checkout that is not part of "
                 "this repository. Set SO_PAINT_REPO=/path/to/so-paint to use it on purpose.")
    repo = pathlib.Path(raw).expanduser().resolve()
    if not (repo / ".venv/bin").is_dir():
        sys.exit(f"UNSUPPORTED: {repo} has no .venv/bin; not a prepared so-paint checkout")
    if args.command == "simulate-bridge":
        command = [str(repo / ".venv/bin/python"), "examples/bridge_simulation.py"]
    else:
        command = [str(repo / ".venv/bin/so-paint"), "--config", "workspace.json"]
        if args.command == "doctor":
            command += ["doctor"]
        else:
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            command += ["pilot-observe", "--output", f"runs/observation-{stamp}"]
    raise SystemExit(subprocess.run(command, cwd=repo, check=False).returncode)


if __name__ == "__main__":
    main()
