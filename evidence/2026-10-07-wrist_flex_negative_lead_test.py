"""wrist_flex NEGATIVE-direction deadband test (GO HQ 2026-10-07). One session. No Astra. No other joint.

For this process only (controller defaults untouched on disk):
  * direction-specific lead for wrist_flex: 0 counts positive, 13 counts negative
    (logs: gap 11 -> 0 counts, gap 13 -> 0, gap 21 -> 8 counts then stuck at 13);
  * max command gap 22 counts (1.934 deg), as in the reverse test;
  * excursion envelope 8 deg.
Sequence: torque ON (proven startup) -> wrist_flex -2 deg -> if reached, return to the start -> torque OFF.
Usage: python 2026-10-07-wrist_flex_negative_lead_test.py --go <out_json>
"""
import json
import pathlib
import sys

if len(sys.argv) != 3 or sys.argv[1] != "--go":
    sys.exit("REFUSED: usage --go <out_json>")
OUT = pathlib.Path(sys.argv[2])
if OUT.exists():
    sys.exit(f"refusing to overwrite {OUT}")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "boris"))
import controller as C  # noqa: E402

JOINT, NEG_LEAD = "wrist_flex", 13
assert C.DEADBAND_LEAD_COUNTS == {"shoulder_pan": 6}
C.DEADBAND_LEAD_COUNTS = {"shoulder_pan": 6, JOINT: (0, NEG_LEAD)}
C.MAX_STEP_COUNTS = 22
C.MAX_EXCURSION_DEG = 8.0

s = {"test": "wrist_flex negative lead", "lead_counts": {"positive": 0, "negative": NEG_LEAD},
     "max_step_counts": C.MAX_STEP_COUNTS, "excursion_deg": C.MAX_EXCURSION_DEG, "requested_delta_deg": -2.0}
try:
    ctl = C.connect(arm=True, joints=[JOINT])
    s["start"] = ctl.get_pose()
    s["negative_move"] = ctl.move_joint_delta(JOINT, -2.0)
    s["pose_after_negative"] = ctl.hold()
    s["return_move"] = ctl.move_joint_to(JOINT, s["start"]["joints_deg"][JOINT])
    s["pose_after_return"] = ctl.hold()
    s["result"] = "NEGATIVE_AND_RETURN_REACHED"
except Exception as e:
    s["result"], s["error"] = "STOPPED", f"{type(e).__name__}: {e}"
finally:
    s["stop"] = C.stop("negative lead test done")
with open(OUT, "x") as f:
    json.dump(s, f, indent=1, default=str)
print(json.dumps(s, indent=1, default=str))
