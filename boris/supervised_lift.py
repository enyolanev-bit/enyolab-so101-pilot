"""Supervised commissioning runner. No Astra. Existing startup/stop, stricter limits.

JSON stdin: {"joint":"wrist_flex","offset_deg":0.8}, {"observe":true}, {"stop":true}.
Offsets ALWAYS refer to the measured origin file, including across restarts.
Each command is followed by fresh side and wide images for agent inspection.
"""
import argparse
import atexit
import json
import math
import pathlib
import select
import signal
import sys
import time

import controller as C
import camera

AXES = ("shoulder_pan", "wrist_flex")
STEP = math.floor(1.0 / C.DEG_PER_COUNT)
ENVELOPE = math.floor(5.0 / C.DEG_PER_COUNT)
SHOULDER_STEP_DEG = 0.5


def joint_step(joint):
    return math.floor(SHOULDER_STEP_DEG / C.DEG_PER_COUNT) if joint == "shoulder_lift" else STEP


def joint_envelope(joint):
    return math.floor(2.0 / C.DEG_PER_COUNT) if joint == "shoulder_lift" else ENVELOPE


def check_goal(joint, goal, present, previous_goal, origin):
    if joint not in AXES:
        raise C.SafetyStop("Only shoulder_pan and wrist_flex are authorized")
    if abs(goal - origin[joint]) > joint_envelope(joint):
        raise C.SafetyStop("Goal exceeds fixed session +/-5 degree envelope")
    if abs(goal - present) > joint_step(joint) or abs(goal - previous_goal) > joint_step(joint):
        raise C.SafetyStop("Goal increment exceeds 1 degree")


class Session(C.SafeFollower):
    def __init__(self, origin, expected=None):
        super().__init__(list(AXES))
        self.origin = dict(origin)
        self.expected = dict(expected if expected is not None else origin)
        self.last_sample = None

    def prepare(self):
        self.open(arm=False)
        pose = self.get_pose()
        if any(abs(pose["raw"][j] - self.expected[j]) * C.DEG_PER_COUNT > 0.5
               for j in C.NAMES):
            raise C.SafetyStop("Pose changed since inspected snapshot: inspect before arming")
        if any(abs(pose["raw"][j]-self.origin[j]) > joint_envelope(j) for j in AXES):
            raise C.SafetyStop("Pose outside original session envelope")
        # configure() rewrites these values. Refuse any actual gain change.
        for reg, field in (("P_Coefficient", "position_p_coefficient"),
                           ("I_Coefficient", "position_i_coefficient"),
                           ("D_Coefficient", "position_d_coefficient")):
            values = self._read_raw(reg)
            if any(v != getattr(self.robot.config, field) for v in values.values()):
                raise C.SafetyStop(f"Existing {reg} differs from startup config; gains unchanged, refusing")
        self._event("supervised_origin", raw=self.origin, step_counts=STEP,
                    envelope_counts=ENVELOPE, gains_match=True)

    def arm(self):
        self._arm(self._read_present())
        self.session_start_raw = dict(self.origin)
        original = self.bus.sync_write
        self.previous_goal = self._read_raw("Goal_Position")

        def guarded_write(reg, values, **kwargs):
            if reg != "Goal_Position":
                raise C.SafetyStop("Supervised runner only accepts position goals")
            present = self._read_present()
            for joint, goal in values.items():
                check_goal(joint, goal, present[joint], self.previous_goal[joint], self.origin)
            result = original(reg, values, **kwargs)
            self.previous_goal.update(values)
            return result
        self.bus.sync_write = guarded_write

    def _check_sample(self, joint, now, prev, step, target_raw, worst):
        super()._check_sample(joint, now, prev, step, target_raw, worst)
        if any(abs(now[j] - self.origin[j]) > joint_envelope(j) for j in AXES):
            raise C.SafetyStop("Measured pose left fixed session envelope")
        timestamp = time.monotonic()
        if self.last_sample and self.last_sample[0] == joint:
            _, last_t, last_raw, last_v = self.last_sample
            interval = timestamp - last_t
            velocity = (now[joint] - last_raw) * C.DEG_PER_COUNT / interval
            if abs(velocity) > 25 or abs(velocity-last_v)/interval > 600:
                raise C.SafetyStop("Unexpected sampled speed/acceleration (>25 deg/s or 600 deg/s^2)")
        else:
            velocity = 0.0
        self.last_sample = (joint, timestamp, now[joint], velocity)

    def step_to_offset(self, joint, offset):
        if joint not in AXES or isinstance(offset, bool) or not math.isfinite(offset) or abs(offset) > 5:
            raise C.Refused("Invalid joint or offset")
        pose = self.get_pose()
        target = self.origin[joint] + round(offset / C.DEG_PER_COUNT)
        if abs(target - pose["raw"][joint]) > joint_step(joint):
            raise C.Refused("Split target into increments of <=1 degree from measured pose")
        # No commissioning probe may go closer to a nearby calibrated hard stop.
        cal = self.robot.calibration[joint]
        if self.origin[joint] - cal.range_min < ENVELOPE and target < self.origin[joint]:
            raise C.Refused("Probe would move toward nearby lower calibrated stop")
        if cal.range_max - self.origin[joint] < ENVELOPE and target > self.origin[joint]:
            raise C.Refused("Probe would move toward nearby upper calibrated stop")
        self.last_sample = None
        # A <=0.4 degree residual is logged as such, never interpreted as pen clearance.
        # This uses the existing contact tolerance; gap, gain and envelope checks stay strict.
        return self.move_joint_to(joint, self._deg(joint, target), accept_within_deg=0.4)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--origin", required=True, type=pathlib.Path)
    ap.add_argument("--evidence", required=True, type=pathlib.Path)
    ap.add_argument("--checked-pose", type=pathlib.Path)
    ap.add_argument("--with-shoulder-lift", action="store_true",
                    help="Requires separate GO: <=0.5 degree steps, +/-2 degree shoulder_lift")
    ap.add_argument("--shoulder-max-step-deg", type=float, choices=(0.5, 1.0), default=0.5,
                    help="1.0 requires additional explicit GO; excursion remains +/-2 degrees")
    ap.add_argument("--go", action="store_true")
    args = ap.parse_args()
    if not args.go:
        ap.error("Explicit supervised session GO required")
    origin = json.loads(args.origin.read_text())["pose"]["raw"]
    global AXES, SHOULDER_STEP_DEG
    SHOULDER_STEP_DEG = args.shoulder_max_step_deg
    if args.with_shoulder_lift:
        AXES = (*AXES, "shoulder_lift")
    C.MAX_EXCURSION_DEG = 5.0
    C.MAX_TRAVEL_DEG = 30.0
    C.MAX_STEP_COUNTS_JOINT = {j: joint_step(j) for j in AXES}
    C.MAX_GAP_CEILING_COUNTS = STEP
    C.STRICT_SESSION_ENVELOPE = True
    C.MAX_GOAL_CHANGE_COUNTS = min(joint_step(j) for j in AXES)
    C.DEADBAND_LEAD_COUNTS = {j: 6 for j in AXES}
    C.SETTLE_S = 0.6
    C.OVERSHOOT_TOL_DEG = 0.5
    expected = json.loads(args.checked_pose.read_text())["pose"]["raw"] if args.checked_pose else origin
    ctl = Session(origin, expected)
    atexit.register(ctl.stop, "process exit")
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: sys.exit(1))
    log = open(args.evidence, "x", buffering=1)

    def emit(kind, **data):
        record = {"kind": kind, "time": time.time(), **data}
        line = json.dumps(record)
        log.write(line + "\n")
        print(line, flush=True)

    def observe():
        frames = [camera.capture(j) for j in ("context_camera", "side_camera")]
        emit("observation", pose=ctl.get_pose(), frames=frames)

    failed = False
    try:
        ctl.prepare()
        observe()
        emit("ready_readonly", instructions="Inspect images; send {arm:true} after visual gate")
        while select.select([sys.stdin], [], [], 90)[0]:
            line = sys.stdin.readline()
            if not line:
                break
            cmd = json.loads(line)
            if cmd == {"stop": True}:
                break
            if cmd == {"arm": True} and ctl.state == "READ_ONLY":
                ctl.arm()
                emit("armed", pose=ctl.get_pose())
            elif cmd == {"observe": True}:
                observe()
            elif set(cmd) == {"joint", "offset_deg"}:
                emit("move", result=ctl.step_to_offset(cmd["joint"], cmd["offset_deg"]))
                observe()
            else:
                raise C.Refused("Unknown command")
    except BaseException as exc:
        failed = True
        emit("fault", error=f"{type(exc).__name__}: {exc}")
    finally:
        stopped = ctl.stop("supervised lift session finished")
        emit("stop", result=stopped)
        log.close()
    return 1 if failed or not stopped.get("torque_off_verified") else 0


if __name__ == "__main__":
    sys.exit(main())
