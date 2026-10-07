"""Official LeRobot teleop (leader -> follower) with a stale-goal guard. GO operator 2026-10-07.

PROVEN 2026-10-07 (operator-confirmed) with the same sequence as evidence/2026-10-07-teleop_official.py;
this copy adds fail-closed checks only (both calibration hashes, USB serials, exit codes, torque-off).
scripts/teleop.sh stays blocked by design; this is the human-authorized teleop path.

1. both calibration files present with the approved SHA-256, both USB adapters present (serial numbers);
2. follower, torque OFF verified: Goal_Position := Present_Position on all 6 servos, read back (addr 42 only);
3. immediately `lerobot-teleoperate` (LeRobot 0.6.1) with max_relative_target and a low fps, for a fixed time;
4. read-only check that all six follower torques are 0 after the official disconnect; if not, a torque-0
   write per servo is attempted and re-read. Any failure -> non-zero exit and an explicit message.
Usage (from the repo root): TELEOP_MAX_REL=5 TELEOP_FPS=30 .venv/bin/python scripts/teleop_official.py 300
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

from serial.tools import list_ports
from lerobot.motors import Motor, MotorNormMode, MotorCalibration
from lerobot.motors.feetech import FeetechMotorsBus

ROOT = pathlib.Path(__file__).resolve().parents[1]
CAL_ROOT = pathlib.Path.home() / ".cache/huggingface/lerobot/calibration"
FOLLOWER = {"serial": "5B7B015207", "port": "/dev/cu.usbmodem5B7B0152071", "id": "follower_nevil",
            "cal": CAL_ROOT / "robots/so_follower/follower_nevil.json",
            "sha": "03b26c3328b557d69b5146d5f316b5f23b760dd13fe7341d7e0b3ebe6b6425c9"}
LEADER = {"serial": "5B7B015440", "port": "/dev/cu.usbmodem5B7B0154401", "id": "pilot001_leader",
          "cal": CAL_ROOT / "teleoperators/so_leader/pilot001_leader.json",
          "sha": "183455cd72f827f5084fed6127a2397bff45615f5897cda53276d97e663f5e41"}
NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
MAX_REL_CAP, FPS_CAP, SECONDS_CAP = 5.0, 30, 1800.0          # the values proven on 2026-10-07 are the ceiling


class Refused(RuntimeError):
    pass


def fail(msg: str, code: int = 2):
    print(f"REFUSED: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def parse_args():
    try:
        seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
        max_rel = float(os.environ.get("TELEOP_MAX_REL", "2.0"))
        fps = int(os.environ.get("TELEOP_FPS", "15"))
    except ValueError as e:
        fail(f"bad number: {e}")
    if not (0 < seconds <= SECONDS_CAP):
        fail(f"seconds must be in (0, {SECONDS_CAP}]")
    if not (0 < max_rel <= MAX_REL_CAP):
        fail(f"TELEOP_MAX_REL must be in (0, {MAX_REL_CAP}]")
    if not (1 <= fps <= FPS_CAP):
        fail(f"TELEOP_FPS must be in [1, {FPS_CAP}]")
    return seconds, max_rel, fps


def check_arm(arm: dict, name: str) -> dict:
    if not arm["cal"].is_file():
        raise Refused(f"{name} calibration missing: {arm['cal']} (see README, step 2)")
    raw = arm["cal"].read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != arm["sha"]:
        raise Refused(f"{name} calibration sha256 {got} != approved {arm['sha']}")
    hits = [p.device for p in list_ports.comports()
            if (p.serial_number or "") == arm["serial"] and p.device.startswith("/dev/cu.")]
    if hits != [arm["port"]]:
        raise Refused(f"{name}: expected exactly {arm['port']} (USB serial {arm['serial']}), found {hits}")
    return {m: MotorCalibration(**v) for m, v in json.loads(raw).items()}


def follower_bus(calib) -> FeetechMotorsBus:
    motors = {n: Motor(i, "sts3215", MotorNormMode.RANGE_0_100 if n == "gripper" else MotorNormMode.DEGREES)
              for i, n in enumerate(NAMES, 1)}
    bus = FeetechMotorsBus(port=FOLLOWER["port"], motors=motors, calibration=calib)
    bus.connect(handshake=False)
    return bus


def align_goals(calib) -> dict:
    """Torque must be OFF; Goal := Present on all six servos, read back. Raises on any mismatch."""
    bus = follower_bus(calib)
    try:
        ids = {i: bus.ping(i) for i in range(1, 7)}
        if any(v != 777 for v in ids.values()):
            raise Refused(f"follower ids/models {ids} (expected 1..6 = 777)")
        torque = bus.sync_read("Torque_Enable", normalize=False, num_retry=2)
        if any(v != 0 for v in torque.values()):
            raise Refused(f"follower torque not OFF before start {torque}: cut the 12 V, wait, retry")
        present = bus.sync_read("Present_Position", normalize=False, num_retry=2)
        for m, v in present.items():
            bus.write("Goal_Position", m, v, normalize=False)
        goal = bus.sync_read("Goal_Position", normalize=False, num_retry=2)
        if goal != present:
            raise Refused(f"goal readback {goal} != present {present}")
        return present
    finally:
        bus.port_handler.closePort()


def verify_torque_off(calib) -> bool:
    """Read all six torques; if any is not 0, write 0 per servo and re-read. Returns True only if all are 0."""
    bus = follower_bus(calib)
    try:
        torque = bus.sync_read("Torque_Enable", normalize=False, num_retry=2)
        print("TORQUE_AFTER", torque, flush=True)
        if all(v == 0 for v in torque.values()):
            return True
        for m in NAMES:
            try:
                bus.write("Torque_Enable", m, 0, normalize=False)
            except Exception as e:
                print(f"torque-off write failed on {m}: {e}", file=sys.stderr, flush=True)
        torque = bus.sync_read("Torque_Enable", normalize=False, num_retry=2)
        print("TORQUE_AFTER_RETRY", torque, flush=True)
        return all(v == 0 for v in torque.values())
    finally:
        bus.port_handler.closePort()


def main() -> int:
    seconds, max_rel, fps = parse_args()
    try:
        f_cal = check_arm(FOLLOWER, "follower")
        check_arm(LEADER, "leader")
        print("ALIGNED", align_goals(f_cal), flush=True)
    except Exception as e:                      # nothing was enabled: refuse before any torque
        fail(f"{type(e).__name__}: {e}")
    cmd = [str(ROOT / ".venv/bin/lerobot-teleoperate"),
           "--robot.type=so101_follower", f"--robot.port={FOLLOWER['port']}", f"--robot.id={FOLLOWER['id']}",
           f"--robot.max_relative_target={max_rel}",
           "--teleop.type=so101_leader", f"--teleop.port={LEADER['port']}", f"--teleop.id={LEADER['id']}",
           f"--fps={fps}", f"--teleop_time_s={seconds}"]
    print("RUN", " ".join(cmd[1:]), flush=True)
    t0 = time.monotonic()
    try:
        rc = subprocess.run(cmd, stdin=subprocess.DEVNULL).returncode
    except KeyboardInterrupt:
        rc = 130
    print(f"lerobot-teleoperate exit {rc} after {time.monotonic() - t0:.1f}s", flush=True)
    try:
        off = verify_torque_off(f_cal)
    except Exception as e:
        print(f"TORQUE OFF NOT VERIFIED ({type(e).__name__}: {e}) -> CUT THE 12 V POWER NOW", file=sys.stderr, flush=True)
        return 3
    if not off:
        print("TORQUE OFF NOT CONFIRMED -> CUT THE 12 V POWER NOW", file=sys.stderr, flush=True)
        return 3
    print("TORQUE_OFF_VERIFIED", flush=True)
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
