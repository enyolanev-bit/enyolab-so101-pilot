"""Closed-loop pen contact: short stroke -> camera -> new ink? -> if not, press a little more (wrist_flex).

    detect_new_mark(before_png, after_png)          camera-only analysis, no robot
    ensure_contact_and_draw_short_line(ctl, ...)    on an ARMED controller with shoulder_pan + wrist_flex
    python contact.py --go                          one standalone contact session (asks for nothing else)

Loop (each try starts and ends at the same pan angle, so the drawing start point is unchanged):
  1. tool-camera frame BEFORE;  2. shoulder_pan +STROKE (short line);  3. frame AFTER;
  4. new ink outside the pen-tip zone, after compensating the camera motion (phase correlation)?
  5. pan back to the start (retrace);  6. no ink -> wrist_flex +STEP toward the paper (gravity side,
     + = tip down per the official FK at the drawing pose), capped at CAP in total; retry.
Stops at the first detected mark, or when the cap / try budget is used. Gains are never changed;
shoulder_lift / elbow_flex are never used. Ink colour: red marker (tune INK_* for another colour).
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import controller as C  # noqa: E402
import camera  # noqa: E402
import painter as P  # noqa: E402

PAN, WRIST = P.PAN, P.WRIST
STROKE_DEG = 3.0                 # proven pan stroke amplitude
WRIST_STEP_DEG = 0.5             # one contact correction
WRIST_CAP_DEG = 2.0              # total correction cap (inside the proven +-2 deg wrist envelope)
MAX_TRIES = 5
TOWARD_PAPER = +1                # wrist_flex sign that lowers the tip (FK + gravity evidence, 2026-10-07)
NEW_INK_MIN_PX = 150             # at 960x540; real no-mark pairs gave 10-20 px, a 9 mm line ~400+ px
AW, AH = 960, 540
TIP_XY = tuple(int(v) for v in os.environ.get("CONTACT_TIP_XY", "405,300").split(","))   # pen tip at 960x540
TIP_RADIUS = int(os.environ.get("CONTACT_TIP_RADIUS", "50"))
INK_SAT_MIN = 45            # any saturated paint on white paper (red, blue, ...); the black brush is not saturated
SLIDE_PX_PER_DEG = 22.0     # logged only (camera inference). 2026-10-07: a "paper slides" reading was FALSE per the operator.


def _load(path) -> np.ndarray:
    from PIL import Image
    return np.asarray(Image.open(path).convert("RGB").resize((AW, AH)), dtype=np.int16)


def ink_mask(rgb: np.ndarray) -> np.ndarray:
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    return (sat > INK_SAT_MIN) & (rgb.max(axis=2) > 40)


def _outside_tip() -> np.ndarray:
    yy, xx = np.mgrid[0:AH, 0:AW]
    return (xx - TIP_XY[0]) ** 2 + (yy - TIP_XY[1]) ** 2 > TIP_RADIUS ** 2


def _shift(m0: np.ndarray, m1: np.ndarray) -> tuple[int, int]:
    if m0.sum() == 0 or m1.sum() == 0:
        return 0, 0
    F, G = np.fft.fft2(m0.astype(float)), np.fft.fft2(m1.astype(float))
    R = G * np.conj(F)
    R /= np.abs(R) + 1e-9
    dy, dx = np.unravel_index(int(np.argmax(np.fft.ifft2(R).real)), m0.shape)
    return int(dx - AW if dx > AW // 2 else dx), int(dy - AH if dy > AH // 2 else dy)


def _dilate(m: np.ndarray, r: int) -> np.ndarray:
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


TIP_BLOB_RADIUS, TIP_FLEX_PX = 120, 25   # ink stuck to the pen tip moves with the tip (marker flex), not the paper


def detect_new_mark(before_png, after_png) -> dict:
    far = _outside_tip()
    m0, m1 = ink_mask(_load(before_png)) & far, ink_mask(_load(after_png)) & far
    dx, dy = _shift(m0, m1)
    yy, xx = np.mgrid[0:AH, 0:AW]
    near_tip = (xx - TIP_XY[0]) ** 2 + (yy - TIP_XY[1]) ** 2 <= TIP_BLOB_RADIUS ** 2
    explained = _dilate(np.roll(np.roll(m0, dy, 0), dx, 1), 6) | _dilate(m0 & near_tip, TIP_FLEX_PX)
    new = m1 & ~explained
    n = int(new.sum())
    return {"new_ink_px": n, "mark": n >= NEW_INK_MIN_PX, "image_shift_px": [dx, dy],
            "ink_before_px": int(m0.sum()), "ink_after_px": int(m1.sum())}


def ensure_contact_and_draw_short_line(ctl, capture=None, log=print, max_tries=MAX_TRIES) -> dict:
    """ctl: ARMED SafeFollower with PAN and WRIST enabled. capture(): returns a frame dict with 'path'."""
    capture = capture or (lambda: camera.capture("tool_camera"))
    start = ctl.get_pose()["joints_deg"]
    pan0, wrist0 = start[PAN], start[WRIST]
    # wrist_flex presses the pen only when the pen lies roughly along the paper. With the recommended setup
    # (pen pointing down) it moves the tip ALONG the paper, so pressing is off unless explicitly enabled.
    cap = min(WRIST_CAP_DEG, float(os.environ.get("CONTACT_WRIST_PRESS_DEG", "0")))
    out = {"tries": [], "wrist_correction_deg": 0.0, "contact": False, "wrist_press_cap_deg": cap}
    if cap == 0.0:
        max_tries = min(max_tries, 2)
    for k in range(1, max_tries + 1):
        before = capture()
        r1 = ctl.move_joint_to(PAN, pan0 + STROKE_DEG, accept_within_deg=P.CONTACT_ACCEPT_DEG)
        after = capture()
        det = detect_new_mark(before["path"], after["path"])
        ctl.move_joint_to(PAN, pan0, accept_within_deg=P.CONTACT_ACCEPT_DEG)        # retrace to the start
        rec = {"try": k, "wrist_correction_deg": out["wrist_correction_deg"], "pan_motion_deg": r1["measured_motion_deg"],
               "before": pathlib.Path(before["path"]).name, "after": pathlib.Path(after["path"]).name, **det}
        if abs(r1["measured_motion_deg"]) > 0.5 and det["ink_before_px"] > 200:
            rec["image_shift_px_per_deg"] = round(float(np.hypot(*det["image_shift_px"])) / abs(r1["measured_motion_deg"]), 1)
            rec["camera_inference_low_shift"] = rec["image_shift_px_per_deg"] < SLIDE_PX_PER_DEG   # informational
        rec["mark_accepted"] = det["mark"]                          # CAMERA_INFERENCE; the human confirms the result
        out["tries"].append(rec)
        log(f"  contact try {k}: new ink {det['new_ink_px']} px -> {'MARK' if rec['mark_accepted'] else 'no mark'} "
            f"(camera inference; wrist correction {out['wrist_correction_deg']:+.1f} deg)")
        if rec["mark_accepted"]:
            out["contact"] = True
            break
        if out["wrist_correction_deg"] + WRIST_STEP_DEG > cap + 1e-9:
            out["reason"] = (f"wrist correction cap {cap} deg reached without a visible mark" if cap else
                             "no visible mark and the pen points down (wrist cannot press): press the pen by hand")
            break
        out["wrist_correction_deg"] += WRIST_STEP_DEG
        ctl.move_joint_to(WRIST, wrist0 + TOWARD_PAPER * out["wrist_correction_deg"],
                          accept_within_deg=P.CONTACT_ACCEPT_DEG)
    else:
        out["reason"] = f"{max_tries} tries without a visible mark"
    out["final_pose"] = ctl.get_pose()["joints_deg"]
    return out


def configure_contact_session() -> None:
    C.MAX_STEP_COUNTS_JOINT = dict(P.CONTACT_GAP_COUNTS)
    C.DEADBAND_LEAD_COUNTS = {**C.DEADBAND_LEAD_COUNTS, **P.CONTACT_LEAD_COUNTS}
    C.MAX_EXCURSION_DEG = max(P.ENVELOPE_DEG.values()) + 1.5   # plan envelope 8 + slack, under the proven pan 10
    C.MAX_TRAVEL_DEG = P.MAX_TRAVEL_CAP_DEG


if __name__ == "__main__":
    if sys.argv[1:] != ["--go"]:
        sys.exit("usage: contact.py --go   (pen on the paper, operator watching, 12 V in reach)")
    configure_contact_session()
    res = {}
    try:
        ctl = C.connect(arm=True, joints=[PAN, WRIST])
        res = ensure_contact_and_draw_short_line(ctl)
    except BaseException as e:
        res["error"] = f"{type(e).__name__}: {e}"[:800]
    finally:
        res["stop"] = C.stop("contact routine done")
    print(json.dumps(res, indent=1, default=str))
