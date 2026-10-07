"""Official LeRobot teleop (leader -> follower) with a stale-goal guard. GO operator 2026-10-07.

PROVEN 2026-10-07 (operator-confirmed): identical to evidence/2026-10-07-teleop_official.py.
scripts/teleop.sh stays blocked by design; this is the human-authorized teleop path.

1. follower, torque OFF verified: Goal_Position := Present_Position on all 6 servos, read back (addr 42 only);
2. immediately `lerobot-teleoperate` (LeRobot 0.6.1) with max_relative_target and a low fps, for a fixed time;
3. read-only check that all six follower torques are 0 after the official disconnect.
Usage (from the repo root): TELEOP_MAX_REL=5 TELEOP_FPS=30 .venv/bin/python scripts/teleop_official.py 300
"""
import hashlib
import json
import pathlib
import subprocess
import sys
import time

from lerobot.motors import Motor, MotorNormMode, MotorCalibration
from lerobot.motors.feetech import FeetechMotorsBus

SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
ROOT = pathlib.Path(__file__).resolve().parents[1]
F_PORT, L_PORT = "/dev/cu.usbmodem5B7B0152071", "/dev/cu.usbmodem5B7B0154401"
F_CAL = pathlib.Path.home() / ".cache/huggingface/lerobot/calibration/robots/so_follower/follower_nevil.json"
F_SHA = "03b26c3328b557d69b5146d5f316b5f23b760dd13fe7341d7e0b3ebe6b6425c9"
NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
MAX_REL, FPS = float(__import__("os").environ.get("TELEOP_MAX_REL", "2.0")), int(__import__("os").environ.get("TELEOP_FPS", "15"))


def follower_bus():
    raw = F_CAL.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == F_SHA, "follower calibration sha mismatch"
    calib = {m: MotorCalibration(**v) for m, v in json.loads(raw).items()}
    motors = {n: Motor(i, "sts3215", MotorNormMode.RANGE_0_100 if n == "gripper" else MotorNormMode.DEGREES)
              for i, n in enumerate(NAMES, 1)}
    bus = FeetechMotorsBus(port=F_PORT, motors=motors, calibration=calib)
    bus.connect(handshake=False)
    return bus


out = {}
bus = follower_bus()
try:
    assert all(bus.ping(i) == 777 for i in range(1, 7)), "follower ids/models"
    torque = bus.sync_read("Torque_Enable", normalize=False, num_retry=2)
    assert all(v == 0 for v in torque.values()), f"follower torque not OFF {torque}"
    present = bus.sync_read("Present_Position", normalize=False, num_retry=2)
    for m, v in present.items():
        bus.write("Goal_Position", m, v, normalize=False)
    goal = bus.sync_read("Goal_Position", normalize=False, num_retry=2)
    assert goal == present, f"goal readback {goal} != present {present}"
    out["aligned"] = present
finally:
    bus.port_handler.closePort()
print("ALIGNED", out["aligned"], flush=True)

cmd = [str(ROOT / ".venv/bin/lerobot-teleoperate"),
       "--robot.type=so101_follower", f"--robot.port={F_PORT}", "--robot.id=follower_nevil",
       f"--robot.max_relative_target={MAX_REL}",
       "--teleop.type=so101_leader", f"--teleop.port={L_PORT}", "--teleop.id=pilot001_leader",
       f"--fps={FPS}", f"--teleop_time_s={SECONDS}"]
print("RUN", " ".join(cmd[1:]), flush=True)
t0 = time.monotonic()
rc = subprocess.run(cmd, stdin=subprocess.DEVNULL).returncode
print(f"lerobot-teleoperate exit {rc} after {time.monotonic() - t0:.1f}s", flush=True)

bus = follower_bus()
try:
    print("TORQUE_AFTER", bus.sync_read("Torque_Enable", normalize=False, num_retry=2), flush=True)
finally:
    bus.port_handler.closePort()
