"""Offline tests for scripts/drawing_library.py: catalog, Astra contract, a real LeRobot dataset round trip,
and the replay sequence against a fake follower. No serial port, no robot, no network.
Run: .venv/bin/python scripts/test_drawing_library_offline.py
"""
import importlib.util
import json
import pathlib
import sys
import tempfile
import types

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("dl", HERE / "drawing_library.py")
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)
results = []


def check(name, cond, detail=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))


def refused(fn):
    try:
        fn()
    except SystemExit as e:
        return e.code == 2
    except Exception:
        return True
    return False


lib = {"bridge": {"description": "simple Golden Gate bridge"}, "house": {"description": "small house with a roof"}}
check("valid replay choice", D.validate_choice({"task": "replay", "drawing": "bridge"}, set(lib))["drawing"] == "bridge")
check("unknown drawing refused", refused(lambda: D.validate_choice({"task": "replay", "drawing": "cat"}, set(lib))))
check("extra key refused", refused(lambda: D.validate_choice({"task": "replay", "drawing": "bridge", "speed": 9}, set(lib))))
check("joint values refused", refused(lambda: D.validate_choice({"task": "move", "shoulder_pan": 90}, set(lib))))
check("refusal accepted", D.validate_choice({"task": "refuse", "reason": "no"}, set(lib))["task"] == "refuse")
check("offline: bridge prompt", D.offline_choice("draw a simple Golden Gate Bridge", lib) == {"task": "replay", "drawing": "bridge"})
check("offline: house prompt", D.offline_choice("une maison? draw a house", lib)["drawing"] == "house")
check("offline: unknown -> refuse", D.offline_choice("draw a cat", lib)["task"] == "refuse")
check("bad names refused", all(refused(lambda n=n: D.check_name(n)) for n in ["", "../x", "A", "a b", "x" * 41]))

# real LeRobot 0.6.1 dataset round trip (action only, like lerobot-record without cameras)
from lerobot.datasets.lerobot_dataset import LeRobotDataset
tmp = pathlib.Path(tempfile.mkdtemp())
D.ROOT = tmp
names = [f"{n}.pos" for n in D.T.NAMES]
feats = {"action": {"dtype": "float32", "shape": (6,), "names": names},
         "observation.state": {"dtype": "float32", "shape": (6,), "names": names}}
ds = LeRobotDataset.create("enyolab/bridge", fps=30, root=tmp / "data/drawings/bridge", features=feats, use_videos=False)
for i in range(60):
    v = np.array([i * 0.1, 0, 0, 10, 0, 5], dtype=np.float32)
    ds.add_frame({"action": v, "observation.state": v, "task": "simple Golden Gate bridge"})
ds.save_episode()
ds.finalize() if hasattr(ds, "finalize") else None
frames, fps = D.load_episode({"root": "data/drawings/bridge", "episode": 0})
check("dataset round trip: 60 frames at 30 fps", len(frames) == 60 and fps == 30, (len(frames), fps))
check("dataset frames are finite with the 6 joint keys", D.check_frames(frames, fps) is None and set(frames[0]) == set(names))
check("NaN frame refused", refused(lambda: D.check_frames(frames[:2] + [dict(frames[0], **{"elbow_flex.pos": float("nan")})], 30)))
check("fps above cap refused", refused(lambda: D.check_frames(frames, 60)))

# replay sequence against a fake follower: preflight before connect, approach, replay, disconnect, torque check
calls = []
D.preflight = lambda: calls.append("preflight") or {}
D.finish = lambda cal, ok: calls.append(f"finish:{ok}") or (0 if ok else 1)


class FakeRobot:
    def __init__(self):
        self.config = types.SimpleNamespace(max_relative_target=D.APPROACH_REL)
        self.pos = {k: 30.0 for k in names}
        self.sent = []

    def connect(self, calibrate=False):
        calls.append("connect")

    def get_observation(self):
        return dict(self.pos)

    def send_action(self, a):
        lim = self.config.max_relative_target
        for k, v in a.items():
            self.pos[k] += max(-lim, min(lim, v - self.pos[k]))
        self.sent.append((lim, dict(a)))
        return a

    def disconnect(self):
        calls.append("disconnect")


fake = FakeRobot()
D.make_follower = lambda max_rel: fake
import lerobot.utils.robot_utils as RU
RU.precise_sleep = lambda s: None
entry = {"root": "data/drawings/bridge", "episode": 0, "follower_calibration_sha256": D.T.FOLLOWER["sha"]}
code = D.replay_entry("bridge", entry, assume_yes=True)
approach = fake.sent[:-60]
replay = fake.sent[-60:]
check("replay: preflight before connect, disconnect then torque check, exit 0",
      code == 0 and calls[:2] == ["preflight", "connect"] and calls[-2:] == ["disconnect", "finish:True"], calls)
check("replay: approach (<= 5 deg/step) then the 60 recorded frames",
      len(approach) > 0 and all(l <= D.APPROACH_REL for l, _ in approach) and [a["shoulder_pan.pos"] for _, a in replay] == [f["shoulder_pan.pos"] for f in frames],
      (len(approach), len(replay)))
check("replay: wrong calibration refused", refused(lambda: D.replay_entry("bridge", dict(entry, follower_calibration_sha256="x"), True)))

# record loop: fake leader moving + handle stuck at 92 %, fake follower; gripper must stay held
class FakeLeader:
    def __init__(self):
        self.t = 0

    def connect(self, calibrate=False):
        calls.append("leader-connect")

    def get_action(self):
        self.t += 1                       # still for 20 reads, then moving 2 deg/read for 200 reads, then still
        x = 0.0 if self.t < 20 else 2.0 * min(self.t - 20, 200)
        return {**{k: x for k in names}, "gripper.pos": 92.0}

    def disconnect(self):
        calls.append("leader-disconnect")


import time as _time
RU.precise_sleep = _time.sleep            # real pacing for the record loop (30 Hz, 5 s)
calls.clear()
fake = FakeRobot()
fake.pos["gripper.pos"] = 3.0
D.make_follower = lambda max_rel: fake
D.make_leader = lambda: FakeLeader()
D.LIB_DIR = tmp / "data/drawings"
D.CATALOG = D.LIB_DIR / "library.json"
D.STILL_S, D.MIN_RECORD_S = 1.0, 2.0
code = D.cmd_record(types.SimpleNamespace(name="house", seconds=20, description="small house"))
entry = D.load_catalog()["drawings"].get("house")
fr, f2 = D.load_episode(entry) if entry else ([], 0)
check("record: starts on motion, stops when still, saved", code == 0 and entry and 150 < entry["frames"] < 400 and len(fr) == entry["frames"] and fr[0]["shoulder_pan.pos"] > 0, (code, entry and entry.get("frames"), len(fr), fr[0]["shoulder_pan.pos"] if fr else None))
check("record: gripper held at the follower start value (not the leader 92 %)",
      all(abs(f["gripper.pos"] - 3.0) < 1e-4 for f in fr) and all(abs(a["gripper.pos"] - 3.0) < 1e-4 for _, a in fake.sent))
check("record: preflight first, both devices disconnected, torque check last",
      calls[0] == "preflight" and "disconnect" in calls and "leader-disconnect" in calls and calls[-1] == "finish:True", calls)
check("record: existing name refused", refused(lambda: D.cmd_record(types.SimpleNamespace(name="house", seconds=20, description="x"))))

# Astra API path with a mocked HTTP response (no network, no credits)
import urllib.request as _u
sys.path.insert(0, str(HERE.parent / "boris"))
import astra as _A
_sent = {}


class _Resp:
    def __init__(self, b): self.b = b.encode()
    def __enter__(self): return self
    def __exit__(self, *x): return False
    def read(self, n=-1): return self.b


def _opener(answer):
    class _Op:
        def open(self, req, timeout=0):
            _sent["body"] = json.loads(req.data)
            return _Resp(json.dumps({"status": "completed", "output": [
                {"type": "message", "content": [{"type": "output_text", "text": answer}]}]}))
    return lambda *a, **k: _Op()


_orig = _u.build_opener
_A.os.environ["OPENAI_API_KEY"] = "sk-test" + "y" * 40
try:
    _u.build_opener = _opener('{"task": "replay", "drawing": "bridge"}')
    ch = D.validate_choice(D.astra_choice("dessine un pont du Golden Gate", lib), set(lib))
    check("astra (mocked API): picks 'bridge'", ch == {"task": "replay", "drawing": "bridge"})
    check("astra request: input mentions JSON, library names only, no joint data",
          "json" in _sent["body"]["input"][0]["content"][0]["text"].lower()
          and "shoulder" not in json.dumps(_sent["body"]))
    _u.build_opener = _opener('{"task": "move", "shoulder_pan.pos": 90}')
    check("astra (mocked API): joint command refused", refused(lambda: D.validate_choice(D.astra_choice("x", lib), set(lib))))
finally:
    _u.build_opener = _orig
    _A.os.environ.pop("OPENAI_API_KEY", None)

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
