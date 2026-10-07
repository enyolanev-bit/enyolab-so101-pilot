"""Drawing library: record a drawing by teleoperation, replay it, and let Astra pick one from a prompt.

    .venv/bin/python scripts/drawing_library.py record bridge --seconds 45 --description "simple Golden Gate bridge"
    .venv/bin/python scripts/drawing_library.py list
    .venv/bin/python scripts/drawing_library.py replay bridge
    .venv/bin/python scripts/drawing_library.py draw "draw a simple Golden Gate Bridge" [--offline-astra] [--dry-run]

record : LeRobot leader/follower + LeRobotDataset (same loop as `lerobot-record`, no camera) into
         data/drawings/<name>/ (git-ignored), one episode; the follower draws while you draw with the leader.
         The follower gripper is held at its start value (the leader handle does not read reliably).
replay : official LeRobot dataset + the same loop as `lerobot-replay`, preceded by an approach (max 5 deg per step at 10 Hz) to the
         recorded start pose. max_relative_target = 5 during replay.
draw   : Astra (OpenAI Responses API, one call, no retry) receives the prompt and the library names and
         descriptions, and answers {"task":"replay","drawing":"<name>"} or {"task":"refuse","reason":"..."}.
         Astra never sends joint values: it can only choose a recorded drawing.
Every command that moves the arm: both calibrations + USB serials checked, Goal_Position := Present_Position
with torque OFF before LeRobot enables torque, torque verified OFF on all six servos at the end.
Exit codes: 0 ok, 1 run failed (torque verified OFF), 2 refused before torque, 3 torque OFF NOT confirmed (cut 12 V).
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIB_DIR = ROOT / "data" / "drawings"
CATALOG = LIB_DIR / "library.json"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
MAX_REPLAY_REL, REPLAY_FPS_CAP = 5.0, 30
WAIT_START_S, MOTION_DEG, STILL_DEG, STILL_S, MIN_RECORD_S = 120.0, 3.0, 1.0, 5.0, 8.0
APPROACH_REL, APPROACH_HZ, APPROACH_TOL, APPROACH_MAX_S = 5.0, 10, 3.0, 30.0   # 5 deg like teleop (2 deg cannot lift the arm); tol 3 deg

_spec = importlib.util.spec_from_file_location("teleop_official", ROOT / "scripts" / "teleop_official.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)


def say(msg):
    print(msg, flush=True)


# ------------------------------------------------------------------ catalog
def load_catalog() -> dict:
    if not CATALOG.exists():
        return {"drawings": {}}
    data = json.loads(CATALOG.read_text())
    if not isinstance(data.get("drawings"), dict):
        raise ValueError("library.json: 'drawings' must be an object")
    return data


def save_catalog(cat: dict) -> None:
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CATALOG.with_suffix(".tmp")
    tmp.write_text(json.dumps(cat, indent=1))
    tmp.replace(CATALOG)


def check_name(name: str) -> str:
    if not NAME_RE.match(name or ""):
        raise ValueError("drawing name must match [a-z0-9][a-z0-9_-]{0,39}")
    return name


# ------------------------------------------------------------------ safety wrappers
def preflight() -> dict:
    """Both calibrations and USB serials, then Goal := Present with torque OFF. Returns follower calibration."""
    f_cal = T.check_arm(T.FOLLOWER, "follower")
    T.check_arm(T.LEADER, "leader")
    say(f"ALIGNED {T.align_goals(f_cal)}")
    return f_cal


def finish(f_cal, ok: bool) -> int:
    try:
        off = T.verify_torque_off(f_cal)
    except Exception as e:
        say(f"TORQUE OFF NOT VERIFIED ({type(e).__name__}: {e}) -> CUT THE 12 V POWER NOW")
        return 3
    if not off:
        say("TORQUE OFF NOT CONFIRMED -> CUT THE 12 V POWER NOW")
        return 3
    say("TORQUE_OFF_VERIFIED")
    return 0 if ok else 1


# ------------------------------------------------------------------ record
def make_leader():
    from lerobot.teleoperators.so_leader import SO101Leader, SO101LeaderConfig
    return SO101Leader(SO101LeaderConfig(port=T.LEADER["port"], id=T.LEADER["id"]))


def make_dataset(name: str, root: pathlib.Path, fps: int):
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    keys = [f"{n}.pos" for n in T.NAMES]
    feats = {"action": {"dtype": "float32", "shape": (6,), "names": keys},
             "observation.state": {"dtype": "float32", "shape": (6,), "names": keys}}
    return LeRobotDataset.create(f"enyolab/{name}", fps=fps, root=root, features=feats, use_videos=False)


def cmd_record(a) -> int:
    """LeRobot leader/follower + LeRobotDataset, same loop as lerobot-record, but the follower gripper is HELD
    at its start value (2026-10-07: the leader handle reads a constant ~92 % and opened the gripper)."""
    import numpy as np
    from lerobot.utils.robot_utils import precise_sleep
    name = check_name(a.name)
    if not (10 <= a.seconds <= 300):
        T.fail("--seconds (maximum recording length) must be in [10, 300]")
    root = LIB_DIR / name
    if root.exists():
        T.fail(f"{root} already exists: choose another name or delete it yourself")
    try:
        f_cal = preflight()
    except Exception as e:
        T.fail(f"{type(e).__name__}: {e}")
    fps, keys = 30, [f"{n}.pos" for n in T.NAMES]
    ok, n_frames, leader, robot, ds = False, 0, None, None, None
    try:
        leader, robot = make_leader(), make_follower(MAX_REPLAY_REL)
        leader.connect(calibrate=False)
        robot.connect(calibrate=False)
        hold = robot.get_observation()["gripper.pos"]
        ds = make_dataset(name, root, fps)
        say(f"gripper held at {hold:.1f} %")
        # start on the first leader motion (the operator cannot see this terminal), stop after STILL_S of stillness
        ref = {k: float(v) for k, v in leader.get_action().items()}
        say(f">>> waiting up to {WAIT_START_S:.0f} s for the leader to move (> {MOTION_DEG} deg) <<<")
        t_wait = time.monotonic() + WAIT_START_S
        while True:
            now = {k: float(v) for k, v in leader.get_action().items()}
            if max(abs(now[k] - ref[k]) for k in keys if k != "gripper.pos") > MOTION_DEG:
                break
            if time.monotonic() > t_wait:
                raise RuntimeError(f"the leader did not move within {WAIT_START_S:.0f} s: nothing recorded")
            precise_sleep(1 / fps)
        say(">>> recording: draw now; it stops after 5 s without leader motion <<<")
        t_end, last_move, prev = time.monotonic() + a.seconds, time.monotonic(), now
        while time.monotonic() < t_end:
            t0 = time.perf_counter()
            act = {k: float(v) for k, v in leader.get_action().items()}
            if max(abs(act[k] - prev[k]) for k in keys if k != "gripper.pos") > STILL_DEG:
                last_move, prev = time.monotonic(), dict(act)
            elif time.monotonic() - last_move > STILL_S and time.monotonic() > t_end - a.seconds + MIN_RECORD_S:
                break
            act["gripper.pos"] = hold
            obs = robot.get_observation()
            robot.send_action(dict(act))
            ds.add_frame({"action": np.array([act[k] for k in keys], dtype=np.float32),
                          "observation.state": np.array([obs[k] for k in keys], dtype=np.float32),
                          "task": a.description})
            n_frames += 1
            precise_sleep(max(1 / fps - (time.perf_counter() - t0), 0.0))
        ok = True
    except KeyboardInterrupt:
        say("interrupted")
    except Exception as e:
        say(f"STOPPED: {type(e).__name__}: {e}")
    finally:
        for dev in (robot, leader):
            try:
                if dev is not None:
                    dev.disconnect()
            except Exception as e:
                say(f"disconnect failed: {type(e).__name__}: {e}")
    code = finish(f_cal, ok)
    if ok and code == 0 and n_frames > 0:
        ds.save_episode()
        if hasattr(ds, "finalize"):
            ds.finalize()
        cat = load_catalog()
        cat["drawings"][name] = {"description": a.description, "root": f"data/drawings/{name}", "episode": 0,
                                 "seconds": a.seconds, "frames": n_frames, "gripper_held_pct": round(hold, 1),
                                 "recorded_at": dt.datetime.now().astimezone().isoformat(),
                                 "follower_calibration_sha256": T.FOLLOWER["sha"]}
        save_catalog(cat)
        say(f"saved '{name}' ({n_frames} frames) in {CATALOG.relative_to(ROOT)}")
    return code


# ------------------------------------------------------------------ replay
def load_episode(entry: dict):
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    from lerobot.utils.constants import ACTION
    root = ROOT / entry["root"]
    ds = LeRobotDataset(f"enyolab/{pathlib.Path(entry['root']).name}", root=root, episodes=[entry["episode"]])
    names = ds.features[ACTION]["names"]
    frames = [{n: float(ds[i][ACTION][k]) for k, n in enumerate(names)} for i in range(ds.num_frames)]
    return frames, ds.fps


def check_frames(frames: list[dict], fps) -> None:
    if not frames:
        raise ValueError("episode has no frames")
    if not (1 <= fps <= REPLAY_FPS_CAP):
        raise ValueError(f"episode fps {fps} outside [1, {REPLAY_FPS_CAP}]")
    keys = set(frames[0])
    expected = {f"{n}.pos" for n in T.NAMES}
    if keys != expected:
        raise ValueError(f"unexpected action keys {sorted(keys)}")
    for f in frames:
        if set(f) != keys or not all(math.isfinite(v) for v in f.values()):
            raise ValueError("non-finite or inconsistent action frame")


def make_follower(max_rel: float):
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
    return SO101Follower(SO101FollowerConfig(port=T.FOLLOWER["port"], id=T.FOLLOWER["id"],
                                             max_relative_target=max_rel, use_degrees=True))


def replay_entry(name: str, entry: dict, assume_yes: bool) -> int:
    from lerobot.processor import make_default_robot_action_processor
    from lerobot.utils.robot_utils import precise_sleep
    if entry.get("follower_calibration_sha256") != T.FOLLOWER["sha"]:
        T.fail(f"'{name}' was recorded with another follower calibration: re-record it")
    try:
        frames, fps = load_episode(entry)
        check_frames(frames, fps)
    except Exception as e:
        T.fail(f"cannot load '{name}': {type(e).__name__}: {e}")
    start = frames[0]
    say(f"'{name}': {len(frames)} frames at {fps} fps ({len(frames) / fps:.1f} s). Start pose (deg): "
        + ", ".join(f"{k.removesuffix('.pos')} {v:.1f}" for k, v in start.items()))
    say("Put the pen on a CLEAN spot of the paper at the drawing's start, follower close to that start pose.")
    if not assume_yes and input("Area clear, you are watching, hand near the 12 V switch. Type GO: ").strip() != "GO":
        T.fail("cancelled", code=2)
    try:
        f_cal = preflight()
    except Exception as e:
        T.fail(f"{type(e).__name__}: {e}")
    ok = False
    robot = make_follower(APPROACH_REL)
    try:
        robot.connect(calibrate=False)
        say("approach: slowly to the recorded start pose")
        t_end = time.monotonic() + APPROACH_MAX_S
        while True:
            obs = robot.get_observation()
            err = max(abs(obs[k] - v) for k, v in start.items() if k != "gripper.pos")
            if err <= APPROACH_TOL:
                break
            if time.monotonic() > t_end:
                raise RuntimeError(f"start pose not reached in {APPROACH_MAX_S:.0f} s (max error {err:.1f} deg)")
            robot.send_action(dict(start))
            precise_sleep(1 / APPROACH_HZ)
        robot.config.max_relative_target = MAX_REPLAY_REL
        processor = make_default_robot_action_processor()
        say("replay")
        for action in frames:                                  # same loop as lerobot-replay (0.6.1)
            t0 = time.perf_counter()
            obs = robot.get_observation()
            robot.send_action(processor((dict(action), obs)))
            precise_sleep(max(1 / fps - (time.perf_counter() - t0), 0.0))
        ok = True
    except KeyboardInterrupt:
        say("interrupted")
    except Exception as e:
        say(f"STOPPED: {type(e).__name__}: {e}")
    finally:
        try:
            robot.disconnect()                                # LeRobot: torque OFF on disconnect
        except Exception as e:
            say(f"disconnect failed: {type(e).__name__}: {e}")
    return finish(f_cal, ok)


def cmd_replay(a) -> int:
    name = check_name(a.name)
    entry = load_catalog()["drawings"].get(name)
    if entry is None:
        T.fail(f"unknown drawing '{name}' (see: drawing_library.py list)")
    return replay_entry(name, entry, a.yes)


def cmd_list(a) -> int:
    cat = load_catalog()["drawings"]
    if not cat:
        say("library empty: record a drawing first")
    for n, e in cat.items():
        say(f"{n:20s} {e['seconds']:>4}s  {e['description']}  ({e['recorded_at'][:16]})")
    return 0


# ------------------------------------------------------------------ Astra choice
ASTRA_INSTRUCTIONS = """You are Astra. A robot arm can only REPLAY drawings that a human recorded before.
Given the user's request and the library (name + description), choose the ONE drawing that best matches,
or refuse if none matches. You never output motor values. Answer with JSON only, exactly one of:
  {"task": "replay", "drawing": "<name from the library>"}
  {"task": "refuse", "reason": "<short>"}"""


def validate_choice(raw, names) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("Astra answer must be a JSON object")
    if raw.get("task") == "refuse" and set(raw) == {"task", "reason"} and isinstance(raw["reason"], str):
        return {"task": "refuse", "reason": raw["reason"][:300]}
    if raw.get("task") == "replay" and set(raw) == {"task", "drawing"} and raw["drawing"] in names:
        return {"task": "replay", "drawing": raw["drawing"]}
    raise ValueError(f"off-contract Astra answer {json.dumps(raw)[:200]}")


STOPWORDS = {"draw", "dessine", "dessiner", "please", "the", "and", "with", "une", "des", "les", "simple", "small"}


def _words(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 3 and w not in STOPWORDS}


def offline_choice(prompt: str, library: dict) -> dict:
    """Zero-credit stand-in for Astra: keyword overlap between the prompt and name + description."""
    words = _words(prompt)
    scores = {n: len(words & _words(n + " " + e["description"])) for n, e in library.items()}
    best = max(scores, key=scores.get, default=None)
    if best and scores[best] > 0:
        return {"task": "replay", "drawing": best}
    return {"task": "refuse", "reason": "no recorded drawing matches"}


def astra_choice(prompt: str, library: dict) -> dict:
    sys.path.insert(0, str(ROOT / "boris"))
    import astra as A                                        # reuses the key handling + strict JSON parsing
    import urllib.request
    key = A._api_key()
    lib = [{"name": n, "description": e["description"]} for n, e in library.items()]
    body = {"model": A.MODEL, "store": False, "max_output_tokens": 300, "instructions": ASTRA_INSTRUCTIONS,
            "text": {"format": {"type": "json_object"}},
            "input": [{"role": "user", "content": [{"type": "input_text", "text": "Return JSON. " + json.dumps(
                {"user_request": prompt, "library": lib})}]}]}
    req = urllib.request.Request(A.API_URL, data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=60) as r:
            text = r.read(1_000_000).decode()
    except Exception as e:
        raise A.AstraError(f"Astra request failed: {type(e).__name__}") from None
    if key in text:
        raise A.AstraError("response suppressed (contained the key)")
    res = A._strict_json(text)
    texts = [c["text"] for it in res.get("output", []) if it.get("type") == "message"
             for c in it.get("content", []) if c.get("type") == "output_text"]
    if res.get("status") != "completed" or len(texts) != 1:
        raise A.AstraError("unexpected Astra response shape")
    return A._strict_json(texts[0])


def cmd_draw(a) -> int:
    library = load_catalog()["drawings"]
    if not library:
        T.fail("library empty: record a drawing first")
    if not a.prompt.strip() or len(a.prompt) > 500:
        T.fail("prompt must be 1..500 characters")
    try:
        raw = offline_choice(a.prompt, library) if a.offline_astra else astra_choice(a.prompt, library)
        choice = validate_choice(raw, set(library))
    except Exception as e:
        T.fail(f"Astra: {type(e).__name__}: {e}")
    say(f"Astra -> {json.dumps(choice)}")
    if choice["task"] == "refuse" or a.dry_run:
        return 0
    return replay_entry(choice["drawing"], library[choice["drawing"]], a.yes)


def main() -> int:
    from lerobot.utils.utils import init_logging  # noqa: F401  (fail early if LeRobot is missing)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("name")
    r.add_argument("--seconds", type=float, default=45)
    r.add_argument("--description", required=True)
    p = sub.add_parser("replay")
    p.add_argument("name")
    p.add_argument("--yes", action="store_true", help="skip the typed GO (supervised use only)")
    sub.add_parser("list")
    d = sub.add_parser("draw")
    d.add_argument("prompt")
    d.add_argument("--offline-astra", action="store_true")
    d.add_argument("--dry-run", action="store_true")
    d.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    return {"record": cmd_record, "replay": cmd_replay, "list": cmd_list, "draw": cmd_draw}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
