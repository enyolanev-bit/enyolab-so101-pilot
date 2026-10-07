"""Safe demo / verification CLI for the SO-101 follower. No model (Astra) call anywhere.

    python demo_move.py check                       read-only: identity, IDs, torque OFF, calibration, pose
    python demo_move.py camera [--camera NAME]      one frame (tool_camera | context_camera)
    python demo_move.py move --joint shoulder_pan --delta 3 [--return]
                                                    torque ON, one bounded move, optional return, torque OFF

`move` asks you to type GO (or pass --go). Watch the arm, keep the 12 V switch in reach.
Every run writes a JSON summary in logs/ (and the controller writes a full JSONL event log).
"""
import argparse
import datetime as dt
import json
import pathlib
import sys
import time
import threading
import hashlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import controller  # noqa: E402
import camera  # noqa: E402
import painter  # noqa: E402


def save(summary):
    controller.LOG_DIR.mkdir(exist_ok=True)
    path = controller.LOG_DIR / f"demo-{summary['command']}-{dt.datetime.now().strftime('%Y%m%dT%H%M%S%f')}.json"
    with open(path, "x") as f:
        json.dump(summary, f, indent=1, default=str)
    summary["summary_path"] = str(path)
    print(json.dumps(summary, indent=1, default=str))


def cmd_check(a):
    s = {"command": "check", "started": dt.datetime.now().astimezone().isoformat()}
    try:
        ctl = controller.connect(arm=False)
        s["pose"] = ctl.get_pose()
        s["result"] = "ROBOT_OK"
    except Exception as e:
        s["result"], s["error"] = "ROBOT_NOT_OK", f"{type(e).__name__}: {e}"
    finally:
        s["stop"] = controller.stop("check done")
    save(s)
    return s["result"] == "ROBOT_OK"


def cmd_camera(a):
    s = {"command": "camera", "started": dt.datetime.now().astimezone().isoformat()}
    try:
        s["frame"] = camera.capture(a.camera)
        s["result"] = "CAMERA_OK"
    except Exception as e:
        s["result"], s["error"] = "CAMERA_NOT_OK", f"{type(e).__name__}: {e}"
    save(s)
    return s["result"] == "CAMERA_OK"


def cmd_move(a):
    if not a.go:
        if not sys.stdin.isatty():
            sys.exit("REFUSED: pass --go or run interactively")
        print(f"About to switch torque ON and move {a.joint} by {a.delta:+.1f} deg"
              f"{' and back' if a.ret else ''}.\nArea clear? Hand on the 12 V switch? Type GO: ", end="", flush=True)
        if input().strip() != "GO":
            sys.exit("cancelled")
    if a.contact_gap_deg is not None:
        if a.joint != "shoulder_pan" or not (0 < a.contact_gap_deg <= 2.0):
            sys.exit("REFUSED: --contact-gap-deg is approved for shoulder_pan only, 0 < gap <= 2.0")
        controller.MAX_STEP_COUNTS_JOINT[a.joint] = int(a.contact_gap_deg / controller.DEG_PER_COUNT)
    s = {"command": "move", "joint": a.joint, "delta_deg": a.delta, "return": a.ret,
         "contact_gap_counts": controller.MAX_STEP_COUNTS_JOINT.get(a.joint), "started": dt.datetime.now().astimezone().isoformat(), "moves": []}
    try:
        ctl = controller.connect(arm=True, joints=[a.joint])
        s["pose_start"] = ctl.get_pose()
        s["moves"].append(ctl.move_joint_delta(a.joint, a.delta))
        time.sleep(1.0)
        s["pose_after_move"] = ctl.hold()
        if a.ret:
            s["moves"].append(ctl.move_joint_to(a.joint, s["pose_start"]["joints_deg"][a.joint]))
            time.sleep(1.0)
            s["pose_after_return"] = ctl.hold()
        s["result"] = "MOVE_OK"
    except Exception as e:
        s["result"], s["error"] = "MOVE_STOPPED", f"{type(e).__name__}: {e}"
    finally:
        s["stop"] = controller.stop("demo done")
        if not (s["stop"] or {}).get("torque_off_verified"):
            s["result"] = "TORQUE_OFF_NOT_VERIFIED_CUT_12V"
    save(s)
    return s["result"] == "MOVE_OK"


def cmd_line(a):
    """Deterministic physical proof only. No model call or automatic wrist pressure."""
    if not a.go:
        if not sys.stdin.isatty():
            sys.exit("REFUSED: supervised prepared contact required; pass --go or run interactively")
        print("Loaded brush lightly on clean paper; operator present, area clear, power cutoff ready.", flush=True)
        if input("One shoulder_pan +3 degree stroke, then torque OFF. Type GO: ").strip() != "GO":
            sys.exit("cancelled")
    s = {"command": "line", "started": dt.datetime.now().astimezone().isoformat(),
         "delta_deg": 3.0, "joints": ["shoulder_pan"], "frames_before": [], "frames_after": [],
         "frames_during": [], "physical_mark": "PENDING_IMAGE_REVIEW", "length_mm": None,
         "astra_used": False}
    watcher = None

    def capture_during():
        try:
            s["frames_during"].append(camera.capture("side_camera"))
        except Exception as exc:
            s["frames_during"].append({"error": f"{type(exc).__name__}: {exc}"})

    try:
        # A failed required camera prevents arming. Capture native frames with identity,
        # timestamp and SHA-256; compare actual paper marks after torque is off.
        for name in ("side_camera", "tool_camera", "context_camera"):
            s["frames_before"].append(camera.capture(name))
        painter.configure_pan_line()
        ctl = controller.connect(arm=True, joints=["shoulder_pan"])
        s["controller_log"] = str(ctl._log.name)
        watcher = threading.Thread(target=capture_during, daemon=True)
        watcher.start()
        s["draw"] = painter.draw_pan_line(ctl, delta_deg=3.0)
        s["result"] = "MOTION_COMPLETED_MARK_UNVERIFIED"
    except BaseException as exc:
        s["result"], s["error"] = "STOPPED", f"{type(exc).__name__}: {exc}"
    finally:
        # Stop before waiting for images or doing any image analysis.
        s["stop"] = controller.stop("deterministic pan line finished")
        if not (s["stop"] or {}).get("torque_off_verified"):
            s["result"] = "TORQUE_OFF_NOT_VERIFIED"
        if watcher is not None:
            watcher.join(timeout=35)
            if watcher.is_alive():
                s["camera_worker_timeout"] = True
        for name in ("side_camera", "tool_camera", "context_camera"):
            try:
                s["frames_after"].append(camera.capture(name))
            except Exception as exc:
                s["frames_after"].append({"camera": name, "error": str(exc)})
        if s.get("controller_log"):
            s["controller_log_sha256"] = hashlib.sha256(pathlib.Path(s["controller_log"]).read_bytes()).hexdigest()
        save(s)
    return s["result"] == "MOTION_COMPLETED_MARK_UNVERIFIED"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    c = sub.add_parser("camera")
    c.add_argument("--camera", default="tool_camera")
    m = sub.add_parser("move")
    m.add_argument("--joint", required=True, choices=controller.JOINTS)
    m.add_argument("--delta", required=True, type=float, help="degrees, |delta| <= 10")
    m.add_argument("--return", dest="ret", action="store_true", help="move back to the start afterwards")
    m.add_argument("--go", action="store_true", help="skip the typed confirmation")
    m.add_argument("--contact-gap-deg", type=float, default=None,
                   help="larger command gap for pen/brush contact strokes (max 2.0, approved for shoulder_pan)")
    line = sub.add_parser("line", help="one deterministic pan +3 deg contact stroke, then torque OFF; no Astra")
    line.add_argument("--go", action="store_true", help="operator has prepared contact and is supervising")
    a = ap.parse_args()
    ok = {"check": cmd_check, "camera": cmd_camera, "move": cmd_move, "line": cmd_line}[a.cmd](a)
    sys.exit(0 if ok else 1)
