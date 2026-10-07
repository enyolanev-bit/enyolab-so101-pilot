"""Offline tests for scripts/teleop_official.py. No serial port, no robot: everything is faked.

Run: .venv/bin/python scripts/test_teleop_official_offline.py   (exit 0 = all checks passed)
"""
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import types

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("teleop", HERE / "teleop_official.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)

results = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


CAL = {n: {"id": i, "drive_mode": 0, "homing_offset": 0, "range_min": 0, "range_max": 4095}
       for i, n in enumerate(T.NAMES, 1)}
tmp = pathlib.Path(tempfile.mkdtemp())
fcal, lcal = tmp / "f.json", tmp / "l.json"
fcal.write_text(json.dumps(CAL))
lcal.write_text(json.dumps(CAL) + " ")
T.FOLLOWER.update(cal=fcal, sha=hashlib.sha256(fcal.read_bytes()).hexdigest())
T.LEADER.update(cal=lcal, sha=hashlib.sha256(lcal.read_bytes()).hexdigest())

state = {"ports": [("/dev/cu.usbmodem5B7B0152071", "5B7B015207"), ("/dev/cu.usbmodem5B7B0154401", "5B7B015440")],
         "torque": {n: 0 for n in T.NAMES}, "torque_after": {n: 0 for n in T.NAMES}, "phase": "before",
         "goal": {}, "present": {n: 2000 + i for i, n in enumerate(T.NAMES)}, "rc": 0, "writes": [],
         "stuck_torque": False}
T.list_ports.comports = lambda: [types.SimpleNamespace(device=d, serial_number=s) for d, s in state["ports"]]


class FakeBus:
    def __init__(self, **k):
        self.port_handler = types.SimpleNamespace(closePort=lambda: None)

    def connect(self, handshake=False):
        pass

    def ping(self, i):
        return 777

    def sync_read(self, reg, normalize=False, num_retry=0):
        if reg == "Torque_Enable":
            return dict(state["torque"] if state["phase"] == "before" else state["torque_after"])
        if reg == "Present_Position":
            return dict(state["present"])
        return dict(state["goal"])

    def write(self, reg, m, v, normalize=False):
        state["writes"].append((state["phase"], reg, m, v))
        if reg == "Goal_Position":
            state["goal"][m] = v
        if reg == "Torque_Enable" and not state["stuck_torque"]:
            state["torque_after"][m] = v


T.FeetechMotorsBus = FakeBus


def fake_run(cmd, stdin=None):
    state["phase"] = "after"
    state["cmd"] = cmd
    return types.SimpleNamespace(returncode=state["rc"])


T.subprocess.run = fake_run


def run(argv=("x", "5"), env=None):
    sys.argv = list(argv)
    import os
    for k in ("TELEOP_MAX_REL", "TELEOP_FPS"):
        os.environ.pop(k, None)
    os.environ.update(env or {})
    state.update(phase="before", writes=[], goal={})
    try:
        return T.main()
    except SystemExit as e:
        return e.code


check("nominal: exit 0, goals aligned to present, only goal writes before teleop",
      run() == 0 and state["goal"] == state["present"] and all(w[1] == "Goal_Position" for w in state["writes"]))
check("both calibration ids and caps passed to lerobot-teleoperate",
      "--robot.id=follower_nevil" in state["cmd"] and "--teleop.id=pilot001_leader" in state["cmd"])
state["rc"] = 1
check("lerobot-teleoperate failure -> exit 1", run() == 1)
state["rc"] = 0
lcal.write_text("tampered")
check("leader calibration sha mismatch -> refused before any bus write", run() == 2 and state["writes"] == [])
lcal.write_text(json.dumps(CAL) + " ")
lcal.unlink()
check("leader calibration missing -> refused", run() == 2 and state["writes"] == [])
lcal.write_text(json.dumps(CAL) + " ")
fcal.write_text(json.dumps(CAL) + "x")
check("follower calibration sha mismatch -> refused", run() == 2 and state["writes"] == [])
fcal.write_text(json.dumps(CAL))
state["ports"] = state["ports"][:1]
check("leader USB adapter missing -> refused", run() == 2 and state["writes"] == [])
state["ports"] = [("/dev/cu.usbmodem5B7B0152071", "5B7B015207"), ("/dev/cu.usbmodem5B7B0154401", "5B7B015440"),
                  ("/dev/cu.usbmodemX", "5B7B015207")]
check("duplicate follower serial -> refused", run() == 2)
state["ports"] = state["ports"][:2]
state["torque"] = {n: 1 for n in T.NAMES}
check("torque already ON at start -> refused, no goal write", run() == 2 and state["writes"] == [])
state["torque"] = {n: 0 for n in T.NAMES}
state["torque_after"] = {n: (1 if n == "elbow_flex" else 0) for n in T.NAMES}
check("torque left ON after teleop -> torque-0 retry succeeds -> exit 0",
      run() == 0 and ("after", "Torque_Enable", "elbow_flex", 0) in state["writes"])
state["torque_after"] = {n: 1 for n in T.NAMES}
state["stuck_torque"] = True
check("torque still ON after retry -> exit 3 (cut 12 V)", run() == 3)
state["stuck_torque"] = False
state["torque_after"] = {n: 0 for n in T.NAMES}
check("max_relative_target above 5 refused", run(env={"TELEOP_MAX_REL": "10"}) == 2)
check("fps above 30 refused", run(env={"TELEOP_FPS": "60"}) == 2)
check("duration above cap refused", run(argv=("x", "99999")) == 2)

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
