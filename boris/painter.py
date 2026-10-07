"""2-DOF contact painter: draws ONE continuous normalised path with shoulder_pan (u) and wrist_flex (v).

The pen/brush tip is placed on the paper by a human at the FIRST point of the path; the path is
drawn relative to that start pose. No pen lift exists (no lift axis is proven), so a drawing is a
single continuous path; retraced segments overlap painted lines.

    validate_command(dict)      strict drawing-command check (the ONLY thing Astra may produce)
    plan(start_joints, command) joint waypoints, auto-fitted inside the joint envelope
    draw_polyline(ctl, plan)    executes on an ARMED controller.SafeFollower (contact mode)

Contact mode (2026-10-07 hardware evidence, HQ/operator-approved values):
    command gap <= 2.0 deg (22 counts) for both drawing joints;
    lead: shoulder_pan 10/10 counts (contact shortfall ~10), wrist_flex +6 / -13 counts
          (negative-direction static shortfall 13-14 counts, proven at the folded drawing pose);
    a stall closer than CONTACT_ACCEPT_DEG (1.0) to a waypoint is accepted (friction), all other aborts stay.
"""
from __future__ import annotations

import math
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import controller as C  # noqa: E402

PAN, WRIST = "shoulder_pan", "wrist_flex"
DRAW_JOINTS = (PAN, WRIST)
BASE_WIDTH_MM, BASE_HEIGHT_MM = 40.0, 18.0
SCALE_RANGE = (0.3, 1.25)
SUBSTEP_DEG = 0.5
ENVELOPE_DEG = {PAN: 8.0, WRIST: 8.0}          # auto-fit keeps every waypoint inside this, from the start pose
MAX_TRAVEL_CAP_DEG = 100.0   # per-joint measured travel per drawing session; excursion stays bounded by ENVELOPE_DEG
MAX_POINTS = 60
CONTACT_GAP_COUNTS = {PAN: 22, WRIST: 22}
CONTACT_LEAD_COUNTS = {"shoulder_pan": (10, 10), "wrist_flex": (6, 13)}
CONTACT_ACCEPT_DEG = 1.0                      # crude drawing: a friction stall within 1 deg of a waypoint is accepted
FLIP_U = os.environ.get("DRAW_FLIP_U", "0") == "1"    # mirror horizontally if the drawing comes out reversed
FLIP_V = os.environ.get("DRAW_FLIP_V", "0") == "1"    # flip vertically if "up" is reversed on your setup
FALLBACK_GAINS = {"u_mm_per_deg_pan": 3.35, "v_mm_per_deg_wrist": 2.0}

# Normalised u (0 left .. 1 right), v (0 bottom .. 1 top). Each is ONE continuous path.
TEMPLATES = {
    "golden_gate_bridge": [                               # starts at its LOWEST point (left tower base)
        (0.25, 0.05), (0.25, 1.00),                       # left tower
        (0.00, 0.25),                                     # left side cable
        (1.00, 0.25),                                     # deck
        (0.75, 1.00),                                     # right side cable
        (0.75, 0.05), (0.75, 1.00),                       # right tower down + retrace
        (0.625, 0.55), (0.50, 0.40), (0.375, 0.55), (0.25, 1.00),   # main cable sag
    ],
    "house": [(0.0, 0.0), (1.0, 0.0), (1.0, 0.6), (0.5, 1.0), (0.0, 0.6), (0.0, 0.0), (1.0, 0.6), (0.0, 0.6), (1.0, 0.0)],
    "zigzag": [(0.0, 0.0), (0.2, 1.0), (0.4, 0.0), (0.6, 1.0), (0.8, 0.0), (1.0, 1.0)],
    "line": [(0.0, 0.5), (1.0, 0.5)],
    "two_strokes": [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)],      # horizontal (pan) then vertical (wrist +): an "L"
}


class CommandError(ValueError):
    pass


def configure_pan_line() -> None:
    """Existing proven contact settings, restricted to a single pan stroke/session."""
    C.MAX_STEP_COUNTS_JOINT = {PAN: CONTACT_GAP_COUNTS[PAN]}
    C.DEADBAND_LEAD_COUNTS = {PAN: CONTACT_LEAD_COUNTS[PAN]}
    C.MAX_EXCURSION_DEG = 6.0
    C.MAX_TRAVEL_DEG = 10.0


def draw_pan_line(ctl, delta_deg=5.0) -> dict:
    """One positive pan-only stroke. No FK, wrist correction, retrace or retry.

    Millimetres require a physical scale measurement; never infer contact or a mark
    from encoder progress. Caller owns startup and unconditional torque-off.
    """
    delta = _num(delta_deg, "pan line delta_deg", 1.0, 6.0)
    before = ctl.get_pose()
    result = ctl.move_joint_to(PAN, before["joints_deg"][PAN] + delta,
                               accept_within_deg=CONTACT_ACCEPT_DEG)
    after = ctl.hold()
    return {"primitive": "pan_line", "delta_deg": delta, "before": before, "after": after,
            "move": result, "length_mm": None, "physical_mark": "PENDING_IMAGE_REVIEW"}


def _num(x, name, lo, hi):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not (lo <= x <= hi):
        raise CommandError(f"{name} must be a finite number in [{lo}, {hi}], got {x!r}")
    return float(x)


def validate_command(cmd) -> dict:
    """Accepts exactly one of:
      {"task": "draw", "template": <name>, "scale": s[, "summary": str]}
      {"task": "draw", "path": [[u, v], ...], "scale": s[, "summary": str]}   (2..60 points, u, v in [0, 1])
      {"task": "refuse", "reason": str}
    """
    if not isinstance(cmd, dict):
        raise CommandError("command must be a JSON object")
    if cmd.get("task") == "refuse":
        if set(cmd) != {"task", "reason"} or not isinstance(cmd["reason"], str) or len(cmd["reason"]) > 300:
            raise CommandError('refuse must be exactly {"task": "refuse", "reason": str<=300}')
        return {"task": "refuse", "reason": cmd["reason"]}
    if cmd.get("task") != "draw":
        raise CommandError("task must be 'draw' or 'refuse'")
    keys = set(cmd) - {"summary"}
    if keys not in ({"task", "template", "scale"}, {"task", "path", "scale"}):
        raise CommandError('draw needs exactly "template" OR "path", plus "scale" (and optional "summary")')
    if "summary" in cmd and (not isinstance(cmd["summary"], str) or len(cmd["summary"]) > 300):
        raise CommandError("summary must be a string <= 300 chars")
    out = {"task": "draw", "scale": _num(cmd["scale"], "scale", *SCALE_RANGE), "summary": cmd.get("summary", "")}
    if "template" in cmd:
        if cmd["template"] not in TEMPLATES:
            raise CommandError(f"template must be one of {sorted(TEMPLATES)}")
        out["template"] = cmd["template"]
        out["path"] = [list(p) for p in TEMPLATES[cmd["template"]]]
    else:
        pts = cmd["path"]
        if not isinstance(pts, list) or not (2 <= len(pts) <= MAX_POINTS):
            raise CommandError(f"path must be a list of 2..{MAX_POINTS} points")
        path = []
        for i, p in enumerate(pts):
            if not isinstance(p, list) or len(p) != 2:
                raise CommandError(f"path[{i}] must be [u, v]")
            path.append([_num(p[0], f"path[{i}].u", 0.0, 1.0), _num(p[1], f"path[{i}].v", 0.0, 1.0)])
        out["template"] = None
        out["path"] = path
    return out


# Informational only: on 2026-10-07 the FK tool axis disagreed by ~90 deg with the operator's view of a
# vertical brush (wrist_flex calibration vs URDF zero UNVERIFIED), so it is never used to refuse a plan.


def tool_axis(joints_deg: dict):
    """Tool z axis in the URDF base frame (official FK); None if kinematics are unavailable."""
    try:
        import numpy as np
        import kinematics as K
        k = K.EEKinematics()
        T = k.k.forward_kinematics(np.array([joints_deg[j] for j in K.ARM], dtype=float))
        return [round(float(v), 3) for v in T[:3, 2]]
    except Exception:
        return None


def fk_gains(joints_deg: dict) -> dict:
    """Tip displacement per degree at the start pose (official LeRobot FK); constants as fallback."""
    try:
        import numpy as np
        import kinematics as K
        k = K.EEKinematics()

        def tip(q):
            return k.k.forward_kinematics(np.array([q[j] for j in K.ARM], dtype=float))[:3, 3] * 1000
        p0 = tip(joints_deg)
        g = {}
        for j, key in ((PAN, "u_mm_per_deg_pan"), (WRIST, "v_mm_per_deg_wrist")):
            q = dict(joints_deg)
            q[j] += 1.0
            g[key] = round(float(np.linalg.norm(tip(q) - p0)), 3)
        g["source"] = "LeRobot RobotKinematics FK at start pose (gripper_frame_link; a pen tip further out draws larger)"
        return g
    except Exception as e:
        return {**FALLBACK_GAINS, "source": f"fallback constants ({type(e).__name__})"}


def plan(start_joints: dict, command: dict, wrist_limits_deg=None) -> dict:
    """wrist_limits_deg = (lo, hi) absolute degrees the wrist may reach (calibrated range minus margin).
    The vertical sense is chosen so the drawing fits on the side where the wrist has room."""
    cmd = command if "path" in command and isinstance(command.get("path"), list) and command.get("task") == "draw" \
        else validate_command(command)
    pts = cmd["path"]
    gains = fk_gains(start_joints)
    su = -1 if FLIP_U else 1
    w_mm, h_mm = BASE_WIDTH_MM * cmd["scale"], BASE_HEIGHT_MM * cmd["scale"]
    u0, v0 = pts[0]
    pan0, wr0 = start_joints[PAN], start_joints[WRIST]
    # span of each joint relative to the start point, then fit inside the envelope and the wrist range
    du = max(abs(u - u0) for u, _ in pts) * w_mm / gains["u_mm_per_deg_pan"]
    up = max(v - v0 for _, v in pts) * h_mm / gains["v_mm_per_deg_wrist"]          # deg of wrist for "up"
    down = max(v0 - v for _, v in pts) * h_mm / gains["v_mm_per_deg_wrist"]
    lo, hi = wrist_limits_deg if wrist_limits_deg else (wr0 - ENVELOPE_DEG[WRIST], wr0 + ENVELOPE_DEG[WRIST])
    room_pos = max(0.0, min(hi - wr0, ENVELOPE_DEG[WRIST]))
    room_neg = max(0.0, min(wr0 - lo, ENVELOPE_DEG[WRIST]))

    def wfit(sv):                     # sv = wrist sign for "v up"
        need_pos, need_neg = (up, down) if sv > 0 else (down, up)
        f = 1.0
        for need, room in ((need_pos, room_pos), (need_neg, room_neg)):
            if need > 1e-9:
                f = min(f, room / need)
        return f
    if FLIP_V:
        sv = +1
    else:
        sv = -1 if wfit(-1) >= wfit(+1) else +1          # default "up" = wrist negative, unless it does not fit
    fit = min(1.0, ENVELOPE_DEG[PAN] / du if du else 1.0, wfit(sv))
    w_mm, h_mm = w_mm * fit, h_mm * fit

    def joints_of(u, v):                                   # u right -> pan +, v up -> wrist (sv)
        return (pan0 + su * (u - u0) * w_mm / gains["u_mm_per_deg_pan"],
                wr0 + sv * (v - v0) * h_mm / gains["v_mm_per_deg_wrist"])

    waypoints = [{"i": 0, "seg": 0, PAN: round(pan0, 3), WRIST: round(wr0, 3)}]
    travel = {PAN: 0.0, WRIST: 0.0}
    prev = (pan0, wr0)
    for n, (u, v) in enumerate(pts[1:], 1):
        tgt = joints_of(u, v)
        dp, dw = tgt[0] - prev[0], tgt[1] - prev[1]
        steps = max(1, math.ceil(max(abs(dp), abs(dw)) / SUBSTEP_DEG - 1e-9))
        for s in range(1, steps + 1):
            waypoints.append({"i": len(waypoints), "seg": n, PAN: round(prev[0] + dp * s / steps, 3),
                              WRIST: round(prev[1] + dw * s / steps, 3)})
        travel[PAN] += abs(dp)
        travel[WRIST] += abs(dw)
        prev = tgt
    exc = {j: max(abs(w[j] - start_joints[j]) for w in waypoints) for j in DRAW_JOINTS}
    problems = [f"{j} excursion {exc[j]:.2f} > {ENVELOPE_DEG[j]}" for j in DRAW_JOINTS if exc[j] > ENVELOPE_DEG[j] + 1e-6]
    problems += [f"{j} travel {travel[j]:.1f} > {MAX_TRAVEL_CAP_DEG}" for j in DRAW_JOINTS if travel[j] > MAX_TRAVEL_CAP_DEG]
    axis = tool_axis(start_joints)
    if fit < 0.3:
        problems.append(f"drawing would be shrunk to {fit:.2f}: not enough wrist_flex room "
                        f"(+{room_pos:.1f} / -{room_neg:.1f} deg); move the wrist away from its stop")
    return {"tool_axis_fk_unverified": axis, "v_up_wrist_sign": sv,
            "wrist_room_deg": [round(room_neg, 2), round(room_pos, 2)], "command": cmd, "size_mm": [round(w_mm, 1), round(h_mm, 1)], "fit_factor": round(fit, 3), "gains": gains,
            "start_joints": {PAN: pan0, WRIST: wr0}, "waypoints": waypoints, "segments": len(pts) - 1,
            "max_excursion_deg": {j: round(v, 3) for j, v in exc.items()},
            "travel_deg": {j: round(v, 3) for j, v in travel.items()}, "problems": problems,
            "estimated_duration_s": round(len(waypoints) * 1.6, 0)}


def summarize(p: dict) -> str:
    c = p["command"]
    return (f"{c.get('template') or 'custom path'} ({len(c['path'])} points, {p['segments']} segments) "
            f"~{p['size_mm'][0]:.0f} x {p['size_mm'][1]:.0f} mm (fit {p['fit_factor']}); "
            f"{len(p['waypoints'])} waypoints; excursion pan {p['max_excursion_deg'][PAN]:.2f} deg, "
            f"wrist {p['max_excursion_deg'][WRIST]:.2f} deg; ~{p['estimated_duration_s']:.0f} s; "
            f"problems: {p['problems'] or 'none'}")


def configure_contact_mode(p: dict) -> None:
    """Controller limits for ONE drawing session (process-local; nothing written to disk)."""
    C.MAX_STEP_COUNTS_JOINT = dict(CONTACT_GAP_COUNTS)
    C.DEADBAND_LEAD_COUNTS = {**C.DEADBAND_LEAD_COUNTS, **CONTACT_LEAD_COUNTS}
    C.MAX_EXCURSION_DEG = max(ENVELOPE_DEG.values()) + 1.5    # slack for the contact check / stall tolerance (<= 10)
    # measured travel also counts small contact overshoots and corrections: 2x the planned path
    C.MAX_TRAVEL_DEG = min(MAX_TRAVEL_CAP_DEG, math.ceil(max(p["travel_deg"].values()) * 2.5) + 2)


def draw_polyline(ctl, p: dict, log=print) -> dict:
    """Execute a plan on an ARMED controller whose session started at p['start_joints']."""
    if p["problems"]:
        raise C.Refused(f"plan problems {p['problems']}")
    pose = ctl.get_pose()["joints_deg"]
    off = {j: abs(pose[j] - p["start_joints"][j]) for j in DRAW_JOINTS}
    if any(v > 0.3 for v in off.values()):
        raise C.Refused(f"pose moved since planning {off}: re-plan")
    out = {"reached": [], "stalled_within": 0}
    n = len(p["waypoints"]) - 1
    for wp in p["waypoints"][1:]:
        for j in DRAW_JOINTS:
            cur = ctl.get_pose()["joints_deg"][j]
            if abs(wp[j] - cur) > C.TOL_DEG:
                r = ctl.move_joint_to(j, wp[j], accept_within_deg=CONTACT_ACCEPT_DEG)
                out["stalled_within"] += bool(r.get("stalled_within"))
        got = ctl.get_pose()["joints_deg"]
        out["reached"].append({"i": wp["i"], "seg": wp["seg"], PAN: got[PAN], WRIST: got[WRIST],
                               "err": {j: round(got[j] - wp[j], 3) for j in DRAW_JOINTS}})
        if wp["i"] % 10 == 0 or wp["i"] == n:
            log(f"  waypoint {wp['i']}/{n} (segment {wp['seg']}/{p['segments']})")
    out["max_abs_error_deg"] = {j: max(abs(r["err"][j]) for r in out["reached"]) for j in DRAW_JOINTS}
    return out
