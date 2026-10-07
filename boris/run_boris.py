"""ONE command: prompt -> Astra drawing command -> safe controller draws it -> camera -> torque OFF.

    python run_boris.py "draw a simple Golden Gate Bridge"
    python run_boris.py "draw a house" --offline-astra      # no API call, zero credits
    python run_boris.py "draw a bridge" --dry-run           # everything except the motors

Sequence:
  1. read-only checks: cameras + robot (identity, IDs, torque OFF, calibration, pose) - no write
  2. fresh camera frames + measured robot state
  3. Astra -> ONE validated drawing command (template or one continuous path) or a refusal
  4. plan (shoulder_pan + wrist_flex only, auto-fitted inside the joint envelope), printed
  5. you place the pen on the paper (it is the FIRST point of the drawing) and type GO
  6. proven safe startup (torque ON) -> draw -> torque OFF, verified
  7. after-images of the result; summary in logs/
Ctrl+C at any time = torque OFF. The 12 V switch is the real emergency stop.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import controller as C  # noqa: E402
import camera  # noqa: E402
import painter as P  # noqa: E402
import astra  # noqa: E402
import contact  # noqa: E402


def say(msg=""):
    print(msg, flush=True)


def wrist_limits(ctl) -> tuple[float, float]:
    """Absolute wrist_flex degrees reachable: calibrated range minus the controller margin."""
    c, m = ctl.robot.calibration[P.WRIST], C.LIMIT_MARGIN[P.WRIST]
    return ctl._deg(P.WRIST, c.range_min + m + 1), ctl._deg(P.WRIST, c.range_max - m - 1)


def read_pose() -> dict:
    ctl = C.connect(arm=False)                     # read-only: no register write
    try:
        pose = ctl.get_pose()
        pose["wrist_limits_deg"] = wrist_limits(ctl)
        return pose
    finally:
        C.stop("read-only pose")


def capture_all(tag: str) -> list[dict]:
    frames = []
    for cam in ("side_camera", "tool_camera", "context_camera"):
        try:
            # All three views must carry image bytes; metadata-only secondary entries
            # were silently omitted from the API's input_image list.
            frames.append(camera.capture_for_astra(camera_name=cam))
        except Exception as e:
            say(f"  ! {cam}: {e}")
    say(f"  {tag}: {len(frames)} frame(s): " + ", ".join(f"{f['camera']} {f['width']}x{f['height']}" for f in frames))
    return frames


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", nargs="?", help='e.g. "draw a simple Golden Gate Bridge" (asked if omitted)')
    ap.add_argument("--offline-astra", action="store_true", help="local keyword planner instead of the API")
    ap.add_argument("--dry-run", action="store_true", help="stop after the plan: no torque, no motion")
    ap.add_argument("--yes", action="store_true", help="skip the typed GO (only for supervised rehearsals)")
    ap.add_argument("--no-contact-check", action="store_true", help="skip the closed-loop pen contact check")
    ap.add_argument("--scale", type=float, default=None, help="override the drawing scale (0.3..1.25)")
    a = ap.parse_args()
    prompt = a.prompt or input("What should the robot draw? > ").strip()
    run = {"started": dt.datetime.now().astimezone().isoformat(), "prompt": prompt, "dry_run": a.dry_run}
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    C.LOG_DIR.mkdir(exist_ok=True)

    def save():
        run["finished"] = dt.datetime.now().astimezone().isoformat()
        safe = json.loads(json.dumps(run, default=str))
        for f in safe.get("frames_before", []) + safe.get("frames_after", []) + safe.get("frames_during", []):
            f.pop("astra_image_data_url", None)
        with open(C.LOG_DIR / f"run-{stamp}.json", "w") as fh:
            json.dump(safe, fh, indent=1)
        say(f"\nlog: logs/run-{stamp}.json")

    try:
        say("1/7 read-only checks")
        pose = read_pose()
        run["pose_before"] = pose
        say(f"  robot OK, torque OFF, pose (deg) { {k: round(v, 1) for k, v in pose['joints_deg'].items()} }")

        say("2/7 cameras")
        frames = capture_all("before")
        run["frames_before"] = frames

        say(f"3/7 Astra ({'offline mapper' if a.offline_astra else astra.MODEL})")
        state = {"joints_deg": pose["joints_deg"], "gripper_pct": pose["gripper_pct"], "torque": "OFF",
                 "drawing_joints": list(P.DRAW_JOINTS), "pen_lift": "not available"}
        prop = astra.propose(prompt, frames, state, offline=a.offline_astra)
        run["astra"] = {k: v for k, v in prop.items() if k != "raw"} | {"raw": prop["raw"]}
        cmd = prop["command"]
        if a.scale is not None and cmd["task"] == "draw":
            cmd = P.validate_command({k: v for k, v in {**cmd, "scale": a.scale}.items()
                                      if k in ("task", "scale", "summary") or (k == "template" and v) or
                                      (k == "path" and not cmd.get("template"))})
            say(f"  scale overridden to {a.scale}")
        say(f"  -> {json.dumps(prop['raw'])}")
        if cmd["task"] == "refuse":
            say(f"  Astra refused: {cmd['reason']}")
            run["result"] = "ASTRA_REFUSED"
            return 2

        say("4/7 plan")
        p = P.plan(pose["joints_deg"], cmd, pose["wrist_limits_deg"])
        run["plan_preview"] = {k: v for k, v in p.items() if k != "waypoints"}
        say("  " + P.summarize(p))
        if p["problems"]:
            run["result"] = "PLAN_REFUSED"
            return 3
        if a.dry_run:
            run["result"] = "DRY_RUN_OK"
            return 0

        say("5/7 human check")
        say("  Put the pen tip ON THE PAPER (not on tape/plastic), touching with light pressure, where the")
        say("  drawing should START (left end for the bridge). Check by eye that the tip really touches.")
        say("  Area clear, you are watching, hand near the 12 V switch.")
        if not a.yes and input("  Type GO to draw: ").strip() != "GO":
            run["result"] = "CANCELLED"
            return 4

        say("6/7 drawing (Ctrl+C = torque OFF)")
        _pose = read_pose()
        p = P.plan(_pose["joints_deg"], cmd, _pose["wrist_limits_deg"])   # re-plan from where the pen actually is
        run["plan"] = {k: v for k, v in p.items() if k != "waypoints"} | {"n_waypoints": len(p["waypoints"])}
        if p["problems"]:
            run["result"] = "PLAN_REFUSED"
            return 3
        contact.configure_contact_session()
        t0 = time.monotonic()
        run["frames_during"] = []
        import threading
        stop_cam = threading.Event()

        def watch():                                   # context frames while drawing (camera only, no bus)
            while not stop_cam.wait(15):
                try:
                    run["frames_during"].append(camera.capture("side_camera"))
                except Exception as e:
                    run["frames_during"].append({"error": str(e)[:200]})
        threading.Thread(target=watch, daemon=True).start()
        try:
            ctl = C.connect(arm=True, joints=list(P.DRAW_JOINTS))
            if not a.no_contact_check:
                say("  pen contact check (short stroke + camera, presses up to +2 deg if no ink)")
                run["contact"] = contact.ensure_contact_and_draw_short_line(ctl, log=say)
                if not run["contact"]["contact"]:
                    raise C.Refused("no visible ink after the contact check: press the pen onto the paper "
                                    f"and retry ({run['contact'].get('reason')})")
                p = P.plan(ctl.get_pose()["joints_deg"], cmd, wrist_limits(ctl))   # start = pose after the contact check
                run["plan"] = {k: v for k, v in p.items() if k != "waypoints"} | {"n_waypoints": len(p["waypoints"])}
            run["draw"] = P.draw_polyline(ctl, p, log=say)
            run["result"] = "MOTION_COMPLETED_MARK_UNVERIFIED"
            run["physical_mark"] = "PENDING_IMAGE_REVIEW"
        except BaseException as e:
            run["result"], run["error"] = "STOPPED", f"{type(e).__name__}: {e}"[:1500]
            say(f"  STOPPED: {run['error'][:300]}")
        finally:
            stop_cam.set()
            run["stop"] = C.stop("drawing finished")
            run["draw_seconds"] = round(time.monotonic() - t0, 1)
            ok = (run["stop"] or {}).get("torque_off_verified")
            if not ok:
                run["result"] = "TORQUE_OFF_NOT_VERIFIED"
            say(f"  torque OFF verified: {ok}" + ("" if ok else "  -> CUT THE 12 V POWER"))

        say("7/7 result images")
        run["frames_after"] = capture_all("after")
        return 0 if run["result"] == "MOTION_COMPLETED_MARK_UNVERIFIED" else 5
    except KeyboardInterrupt:
        run["result"] = "INTERRUPTED"
        run["stop"] = C.stop("interrupted")
        return 130
    except Exception as e:
        run["result"], run["error"] = "ERROR", f"{type(e).__name__}: {e}"[:1500]
        say(f"ERROR: {run['error'][:300]}")
        return 1
    finally:
        save()


if __name__ == "__main__":
    sys.exit(main())
