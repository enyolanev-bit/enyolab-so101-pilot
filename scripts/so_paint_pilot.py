"""Entry point to the adopted sibling so-paint checkout. Observation/simulation only."""

import argparse
import datetime
import pathlib
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["doctor", "observe", "simulate-bridge"])
    args = parser.parse_args()
    repo = pathlib.Path(__file__).resolve().parents[2] / "so-paint"
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
