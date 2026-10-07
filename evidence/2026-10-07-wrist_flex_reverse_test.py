"""wrist_flex reverse recovery test ONLY (GO HQ 2026-10-07). One session, one move. No Astra.

controller.py is NOT modified. For this process only, the per-step command gap is raised
from 1.0 deg to 2.0 deg (22 counts, the largest integer count <= 2.0 deg) via the module
constant, and only wrist_flex is enabled. No deadband lead applies to wrist_flex
(DEADBAND_LEAD_COUNTS == {"shoulder_pan": 6}, asserted). Target = raw 1370, never commanded beyond.

Usage: python 2026-10-07-wrist_flex_reverse_test.py --go <out_json>
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

TARGET_RAW, JOINT = 1370, "wrist_flex"
assert C.DEADBAND_LEAD_COUNTS == {"shoulder_pan": 6}
C.MAX_STEP_COUNTS = int(2.0 / C.DEG_PER_COUNT)          # 22 counts = 1.934 deg, this process only
assert C.MAX_STEP_COUNTS * C.DEG_PER_COUNT <= 2.0

s = {"test": "wrist_flex reverse recovery", "max_step_counts": C.MAX_STEP_COUNTS,
     "max_step_deg": round(C.MAX_STEP_COUNTS * C.DEG_PER_COUNT, 3), "target_raw": TARGET_RAW}
try:
    ctl = C.connect(arm=True, joints=[JOINT])
    start = ctl.get_pose()
    s["start_raw"], s["start_deg"] = start["raw"][JOINT], start["joints_deg"][JOINT]
    target_deg = ctl._deg(JOINT, TARGET_RAW)
    if ctl._to_raw(JOINT, target_deg) != TARGET_RAW:
        raise C.Refused("target degree/raw round trip mismatch")
    if not (0 < start["raw"][JOINT] - TARGET_RAW <= 30):
        raise C.Refused(f"unexpected start raw {start['raw'][JOINT]} (expected ~1391, above 1370)")
    s["target_deg"] = round(target_deg, 3)
    s["move"] = ctl.move_joint_to(JOINT, target_deg)
    s["pose_after"] = ctl.hold()
    s["result"] = "REACHED"
except Exception as e:
    s["result"], s["error"] = "STOPPED", f"{type(e).__name__}: {e}"
finally:
    s["stop"] = C.stop("reverse test done")
with open(OUT, "x") as f:
    json.dump(s, f, indent=1, default=str)
print(json.dumps(s, indent=1, default=str))
