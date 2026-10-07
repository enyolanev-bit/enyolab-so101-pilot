"""Safe, bounded controller for the ENYOLAB SO-101 follower (Pilot #001, Boris / Astra).

Public API (module-level, after connect()):
    connect(arm=False|True, joints=[...])  open the follower; arm=True runs the proven startup
    get_pose()                             measured pose (degrees, gripper %), raw counts, state
    get_camera_frame(camera="tool_camera") one PNG frame + pose read before and after it
    move_joint_delta(joint, degrees)       bounded relative move from the measured pose
    move_joint_to(joint, target_degrees)   bounded move to a fixed target
    set_gripper(percent)                   DISABLED (the gripper holds the tool)
    hold()                                 keep the current goals; verify torque; no writes
    stop()                                 torque OFF on all six servos, verified, port closed

Proven startup (reused from the 2026-10-06 standalone tests):
    USB identity by serial number -> exclusive lock -> LeRobot 0.6.1 source fingerprints
    -> calibration SHA-256 -> IDs 1..6 = STS3215 (777) -> torque OFF on all six
    -> calibration registers == file -> pose inside calibrated ranges
    -> configure() with Goal_Position := Present_Position written and read back
    -> torque ON (the only authorized point) -> 4 s hold with drift check.

Motion limits (all checked BEFORE every write; nothing is silently clipped):
    * at most 1 degree per control step (MAX_STEP_DEG), measured-pose relative;
    * excursion from the session-start pose <= MAX_EXCURSION_DEG per joint;
    * measured travel per joint per session <= MAX_TRAVEL_DEG;
    * calibrated range minus a margin; only enabled joints; gripper never;
    * every other joint watched for drift (> 2 deg / 2 %) -> stop.
Any fault, signal, watchdog expiry or exit -> stop(): torque OFF, read back, port closed.
The model (Astra) must only reach the functions above, never the bus.
"""
from __future__ import annotations

import atexit
import datetime as dt
import fcntl
import hashlib
import importlib.metadata as md
import inspect
import json
import math
import os
import pathlib
import signal
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def _load_env(path: pathlib.Path = HERE / ".env") -> None:
    """Minimal .env reader (KEY=VALUE, # comments). Existing environment wins."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()

# --- identity (override in .env only after a human check) ---------------------------------
FOLLOWER_SERIAL = os.environ.get("FOLLOWER_SERIAL", "5B7B015207")
FOLLOWER_ID = os.environ.get("FOLLOWER_ID", "follower_nevil")
FOLLOWER_CAL_SHA256 = os.environ.get(
    "FOLLOWER_CALIBRATION_SHA256", "f48d50d5ba8c220f13575f13c1d6562d9431391fb1e726541abdaf2c4e714a9d")
CAL_DIR = pathlib.Path(os.environ.get(
    "FOLLOWER_CALIBRATION_DIR",
    str(pathlib.Path.home() / ".cache/huggingface/lerobot/calibration/robots/so_follower"))).expanduser()

# --- limits (code constants on purpose: raising them is a human decision) -----------------
NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
JOINTS = NAMES[:5]                               # the gripper is never movable here
MAX_STEP_DEG = 1.0
MAX_EXCURSION_DEG = 10.0
MAX_TRAVEL_DEG = 10.0
TOL_DEG = 0.3                                    # success band around the target (~3 counts)
# Static error measured on shoulder_pan 2026-10-06/07: the servo stops ~4-6 counts short of its goal
# (a goal 6 counts away produced no motion). For shoulder_pan ONLY, the goal is placed this many
# counts beyond the target, never more than MAX_STEP_COUNTS from the measured pose and never beyond
# the envelope plus this lead. Every other joint is unproven: no lead (goal never beyond target).
# A value may also be a (positive_direction, negative_direction) tuple of counts.
DEADBAND_LEAD_COUNTS = {"shoulder_pan": 6}
SETTLE_S, SAMPLE_S, HOLD_S = 0.4, 0.05, 4.0
DRIFT_TOL = 2.0                                  # degrees, percent for the gripper
REVERSE_TOL_DEG, OVERSHOOT_TOL_DEG, NO_PROGRESS_ITERS = 0.2, 2.0, 3
LIMIT_MARGIN = {m: (5 if m == "wrist_flex" else 20) for m in NAMES}   # raw counts
ALIGN_TOL = POST_ENABLE_TOL = 20                                      # raw counts
IDLE_TIMEOUT_S = min(float(os.environ.get("FOLLOWER_IDLE_TIMEOUT_S", "120")), 600.0)
SESSION_TIMEOUT_S = min(float(os.environ.get("FOLLOWER_SESSION_TIMEOUT_S", "900")), 3600.0)
RES = 4095
DEG_PER_COUNT = 360.0 / RES
MAX_STEP_COUNTS = int(MAX_STEP_DEG / DEG_PER_COUNT)                   # 11 counts = 0.967 deg
# Per-joint override of the command gap (goal vs measured), in counts. Hard ceiling 2.0 deg (22 counts):
# shoulder_pan needs it to push a pen/brush along paper (2026-10-07: stalls at 11 counts in contact).
MAX_GAP_CEILING_COUNTS = int(2.0 / DEG_PER_COUNT)
MAX_STEP_COUNTS_JOINT: dict = {}
# Optional stricter commissioning limits; existing drawing mode retains its defaults.
STRICT_SESSION_ENVELOPE = False
MAX_GOAL_CHANGE_COUNTS = None
LOG_DIR = HERE / "logs"

CONFIG_ADDRS = {40, 55, 7, 85, 41, 18, 33, 21, 22, 23, 16, 28, 36, 42}   # configure() + alignment
MOTION_ADDRS = {40, 42}                                                 # 40 only ever = 0 here
AUDITED = {  # sha256[:16] of inspect.getsource on LeRobot 0.6.1, recorded 2026-10-06
    "SOFollower.configure": "d56e81dad3cf0688", "SOFollower.__init__": "b409d9ebc6077dd9",
    "SerialMotorsBus.torque_disabled": "c5e45d976557d2aa", "SerialMotorsBus.connect": "55089cc557c42960",
    "FeetechMotorsBus.configure_motors": "ff1fdbde15e4aee2", "FeetechMotorsBus.enable_torque": "d6db430cf9fe5780",
    "FeetechMotorsBus.disable_torque": "e8d1eb7a1257426d", "FeetechMotorsBus.is_calibrated": "614e7db2dc531105",
    "GroupSyncWrite.txPacket": "0edf16184c94a5ea", "SerialMotorsBus.write": "94701a0c073db595",
    "SerialMotorsBus._write": "072fe46ea06f5f9f", "SerialMotorsBus.sync_write": "fdd50c8a69fbb538",
    "SerialMotorsBus.sync_read": "d091ea732675e307", "SerialMotorsBus._normalize": "1821a76bdc3a7287",
    "PPH.writeTxRx": "be0d2d386ac5bc0c", "PPH.syncWriteTxOnly": "b0d8b0b58b629811",
}


class SafetyStop(RuntimeError):
    """Raised after the controller has stopped (torque-off attempted) because of a fault."""


class Refused(ValueError):
    """Request rejected before any write; the robot state is unchanged."""


class GripperDisabled(Refused):
    pass


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat()


def _check_static() -> None:
    from lerobot.robots.so_follower.so_follower import SOFollower
    from lerobot.motors.motors_bus import SerialMotorsBus
    from lerobot.motors.feetech.feetech import FeetechMotorsBus
    import scservo_sdk.group_sync_write as gsw
    from scservo_sdk.protocol_packet_handler import protocol_packet_handler as PPH

    if md.version("lerobot") != "0.6.1":
        raise Refused(f"lerobot {md.version('lerobot')} != 0.6.1")
    fns = {"SOFollower.configure": SOFollower.configure, "SOFollower.__init__": SOFollower.__init__,
           "SerialMotorsBus.torque_disabled": SerialMotorsBus.torque_disabled,
           "SerialMotorsBus.connect": SerialMotorsBus.connect,
           "FeetechMotorsBus.configure_motors": FeetechMotorsBus.configure_motors,
           "FeetechMotorsBus.enable_torque": FeetechMotorsBus.enable_torque,
           "FeetechMotorsBus.disable_torque": FeetechMotorsBus.disable_torque,
           "FeetechMotorsBus.is_calibrated": FeetechMotorsBus.is_calibrated.fget,
           "GroupSyncWrite.txPacket": gsw.GroupSyncWrite.txPacket, "SerialMotorsBus.write": SerialMotorsBus.write,
           "SerialMotorsBus._write": SerialMotorsBus._write, "SerialMotorsBus.sync_write": SerialMotorsBus.sync_write,
           "SerialMotorsBus.sync_read": SerialMotorsBus.sync_read,
           "SerialMotorsBus._normalize": SerialMotorsBus._normalize,
           "PPH.writeTxRx": PPH.writeTxRx, "PPH.syncWriteTxOnly": PPH.syncWriteTxOnly}
    for k, f in fns.items():
        h = hashlib.sha256(inspect.getsource(f).encode()).hexdigest()[:16]
        if h != AUDITED[k]:
            raise Refused(f"LeRobot source of {k} changed since audit ({h} != {AUDITED[k]})")
    cal = CAL_DIR / f"{FOLLOWER_ID}.json"
    if not cal.exists():
        raise Refused(f"calibration file missing: {cal.name} (see README_BORIS.md, step 4)")
    got = hashlib.sha256(cal.read_bytes()).hexdigest()
    if got != FOLLOWER_CAL_SHA256:
        raise Refused(f"calibration {cal.name} sha256 {got[:12]}... != pinned {FOLLOWER_CAL_SHA256[:12]}...")


def find_follower_port() -> str:
    """Exactly one USB serial adapter must carry the follower serial number."""
    from serial.tools import list_ports
    hits = [p.device for p in list_ports.comports()
            if (p.serial_number or "") == FOLLOWER_SERIAL and not p.device.startswith("/dev/tty.")]
    if len(hits) != 1:
        raise Refused(f"expected exactly one adapter with serial {FOLLOWER_SERIAL}, found {hits} "
                      f"(plug the follower USB; check FOLLOWER_SERIAL in .env)")
    return hits[0]


class SafeFollower:
    def __init__(self, joints=None):
        joints = list(joints) if joints else os.environ.get("FOLLOWER_ENABLED_JOINTS", "shoulder_pan").split(",")
        joints = [j.strip() for j in joints if j.strip()]
        bad = [j for j in joints if j not in JOINTS]
        if bad or not joints:
            raise Refused(f"enabled joints must be a non-empty subset of {JOINTS}; got {joints}")
        self.enabled = joints
        self.state = "DISCONNECTED"
        self.robot = None
        self.bus = None
        self._lock = threading.RLock()
        self._lockfile = None
        self._log = None
        self._torque_on_allowed = False
        self._allowed = set()
        self.session_start_raw = None
        self.ref_raw = None
        self.travel_deg = {j: 0.0 for j in JOINTS}
        self.armed_at = self.last_cmd = None
        self.last_stop = None
        self._kinematics = None

    # ------------------------------------------------------------------ logging
    def _event(self, kind, **data):
        rec = {"t": _now(), "mono": round(time.monotonic(), 3), "kind": kind, "state": self.state, **data}
        if self._log is not None:
            self._log.write(json.dumps(rec, default=str) + "\n")
            self._log.flush()
        return rec

    # ------------------------------------------------------------------ bus helpers
    def _install_write_guard(self):
        ph = self.bus.packet_handler
        orig_w, orig_s = ph.writeTxRx, ph.syncWriteTxOnly

        def writeTxRx(port, scs_id, address, length, data):
            val = data[0] if length == 1 else (data[0] | (data[1] << 8))
            self._event("write", id=scs_id, addr=address, value=val)
            if address not in self._allowed and not (address == 40 and val == 0):
                raise SafetyStop(f"write to forbidden address {address} (id {scs_id})")
            if address == 40 and val != 0 and not (val == 1 and self._torque_on_allowed):
                raise SafetyStop(f"Torque_Enable={val} outside the authorized point (id {scs_id})")
            return orig_w(port, scs_id, address, length, data)

        def syncWriteTxOnly(port, start_address, data_length, param, param_length):
            self._event("sync_write", addr=start_address, n=param_length // (data_length + 1))
            if start_address not in self._allowed or start_address == 40:
                raise SafetyStop(f"sync_write to forbidden address {start_address}")
            return orig_s(port, start_address, data_length, param, param_length)

        ph.writeTxRx, ph.syncWriteTxOnly = writeTxRx, syncWriteTxOnly
        for m in ("writeTxOnly", "write1ByteTxOnly", "write2ByteTxOnly", "write4ByteTxOnly",
                  "regWriteTxOnly", "regWriteTxRx", "action"):
            setattr(ph, m, lambda *a, _m=m, **k: (_ for _ in ()).throw(SafetyStop(f"{_m} forbidden")))

    def _read_raw(self, reg="Present_Position"):
        try:
            vals = self.bus.sync_read(reg, normalize=False, num_retry=2)
        except SafetyStop:
            raise
        except Exception as e:                       # bus errors become a fault, never a silent retry
            raise SafetyStop(f"{reg}: communication failure ({type(e).__name__}: {e})") from None
        if set(vals) != set(NAMES):
            raise SafetyStop(f"{reg}: missing axes {set(NAMES) - set(vals)}")
        return vals

    def _read_present(self):
        raw = self._read_raw()
        for m, v in raw.items():
            c = self.robot.calibration[m]
            if not (c.range_min <= v <= c.range_max):
                raise SafetyStop(f"{m} raw {v} outside calibrated range [{c.range_min}, {c.range_max}]")
        return raw

    def _mid(self, m):
        c = self.robot.calibration[m]
        return (c.range_min + c.range_max) / 2

    def _deg(self, m, raw):
        return (raw - self._mid(m)) * DEG_PER_COUNT

    def _to_raw(self, m, deg):
        return int(round(deg / DEG_PER_COUNT + self._mid(m)))

    def _pct(self, raw):
        c = self.robot.calibration["gripper"]
        return (min(c.range_max, max(c.range_min, raw)) - c.range_min) / (c.range_max - c.range_min) * 100

    def _pose_from_raw(self, raw):
        return {"t": _now(), "joints_deg": {m: round(self._deg(m, raw[m]), 3) for m in JOINTS},
                "gripper_pct": round(self._pct(raw["gripper"]), 2), "raw": dict(raw), "state": self.state}

    def _in_limits(self, m, raw):
        c, mg = self.robot.calibration[m], LIMIT_MARGIN[m]
        return c.range_min + mg <= raw <= c.range_max - mg

    def _drift(self, raw, exclude=None):
        out = {}
        for m in NAMES:
            if m == exclude:
                continue
            if m == "gripper":
                out[m] = round(self._pct(raw[m]) - self._pct(self.ref_raw[m]), 3)
            else:
                out[m] = round((raw[m] - self.ref_raw[m]) * DEG_PER_COUNT, 3)
        return out

    # ------------------------------------------------------------------ lifecycle
    def open(self, arm: bool = False):
        """arm=False: read-only (no register write). arm=True: proven startup, torque ON."""
        with self._lock:
            if self.state != "DISCONNECTED":
                raise Refused(f"already {self.state}")
            LOG_DIR.mkdir(exist_ok=True)
            self._log = open(LOG_DIR / f"session-{dt.datetime.now().strftime('%Y%m%dT%H%M%S%f')}-{os.getpid()}.jsonl", "x")
            self._event("open", arm=arm, enabled=self.enabled)
            try:
                _check_static()
                port = find_follower_port()
                lock_dir = pathlib.Path.home() / ".cache/enyolab"
                lock_dir.mkdir(parents=True, exist_ok=True)
                self._lockfile = open(lock_dir / f"follower-{FOLLOWER_SERIAL}.lock", "w")
                try:
                    fcntl.flock(self._lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise Refused("another process owns the follower (exclusive lock held)")
                from lerobot.robots.so_follower import SO101FollowerConfig, SO101Follower
                self.robot = SO101Follower(SO101FollowerConfig(
                    port=port, id=FOLLOWER_ID, calibration_dir=CAL_DIR, max_relative_target=MAX_STEP_DEG,
                    use_degrees=True))
                self.bus = self.robot.bus
                self._allowed = set()
                self._install_write_guard()
                self.state = "PRECHECK"
                self.bus.connect()                       # handshake: ping + model reads only
                ids = {i: self.bus.ping(i) for i in range(1, 7)}
                if any(v != 777 for v in ids.values()):
                    raise SafetyStop(f"servo ids/models {ids} (expected 1..6 = 777)")
                torque = self._read_raw("Torque_Enable")
                if any(v != 0 for v in torque.values()):
                    raise SafetyStop(f"torque not OFF at start {torque}")
                if not self.robot.is_calibrated:
                    raise SafetyStop("calibration registers != calibration file")
                p0 = self._read_present()
                out = {m: p0[m] for m in NAMES if not self._in_limits(m, p0[m])}
                if out:
                    raise SafetyStop(f"pose outside calibrated range minus margin {out}")
                self.session_start_raw, self.ref_raw = dict(p0), dict(p0)
                self._event("precheck_ok", port=port, ids=ids, torque=torque, raw=p0)
                if not arm:
                    self.state = "READ_ONLY"
                    return self
                self._arm(p0)
                return self
            except BaseException as e:
                self._fault(f"open failed: {type(e).__name__}: {e}")
                raise

    def _arm(self, p0):
        rb = self.bus
        orig_enable = rb.enable_torque

        def aligned_enable_torque(motors=None, num_retry=0):
            if sys.exc_info()[0] is not None:
                raise SafetyStop(f"configure() failed ({sys.exc_info()[0].__name__}) -> refusing torque enable")
            present = self._read_present()
            for m, v in present.items():
                rb.write("Goal_Position", m, v, normalize=False)
            goal = self._read_raw("Goal_Position")
            present2 = self._read_present()
            bad = {m: (present[m], goal[m], present2[m]) for m in NAMES
                   if goal[m] != present[m] or abs(present2[m] - p0[m]) > ALIGN_TOL or not self._in_limits(m, present2[m])}
            self._event("goal_alignment", written=present, readback=goal, present=present2)
            if bad:
                raise SafetyStop(f"goal alignment failed {bad}")
            self._torque_on_allowed = True
            try:
                orig_enable(motors, num_retry)
            finally:
                self._torque_on_allowed = False
            self.ref_raw = dict(present2)
            self.session_start_raw = dict(present2)

        self.state = "ARMING"
        self._allowed = set(CONFIG_ADDRS)
        rb.enable_torque = aligned_enable_torque
        try:
            self.robot.configure()
        finally:
            rb.enable_torque = orig_enable
            self._allowed = set(MOTION_ADDRS)
        torque = self._read_raw("Torque_Enable")
        if any(v != 1 for v in torque.values()):
            raise SafetyStop(f"partial torque enable {torque}")
        t_end, max_drift = time.monotonic() + HOLD_S, {m: 0 for m in NAMES}
        while time.monotonic() < t_end:
            cur = self._read_present()
            for m in NAMES:
                max_drift[m] = max(max_drift[m], abs(cur[m] - self.ref_raw[m]))
            if any(d > POST_ENABLE_TOL for d in max_drift.values()):
                raise SafetyStop(f"unexpected motion during the 4 s hold {max_drift}")
            time.sleep(SAMPLE_S)
        self.state = "ARMED"
        self.armed_at = self.last_cmd = time.monotonic()
        self._event("armed", hold_max_drift_raw=max_drift, start_raw=self.session_start_raw)
        threading.Thread(target=self._watchdog, daemon=True).start()

    def _watchdog(self):
        while self.state == "ARMED":
            time.sleep(0.5)
            now = time.monotonic()
            if self.state == "ARMED" and (now - self.last_cmd > IDLE_TIMEOUT_S or now - self.armed_at > SESSION_TIMEOUT_S):
                self.stop(f"watchdog: idle {now - self.last_cmd:.0f}s / session {now - self.armed_at:.0f}s")

    def _fault(self, reason):
        self._event("fault", reason=reason)
        return self.stop(reason)

    def stop(self, reason: str = "requested"):
        """Torque OFF servo by servo (bounded retries), read back, close the port. Never raises."""
        with self._lock:
            if self.state == "STOPPED":
                return self.last_stop
            out = {"reason": reason, "torque_zero_writes": {}, "torque_readback": None, "port_closed": None}
            prev, self.state = self.state, "STOPPING"
            bus = self.bus
            try:
                if bus is not None and bus.is_connected:
                    try:
                        bus.port_handler.clearPort()
                        bus.port_handler.is_using = False
                    except Exception:
                        pass
                    already_off = False
                    if prev in ("READ_ONLY", "PRECHECK"):
                        try:
                            already_off = all(v == 0 for v in self._read_raw("Torque_Enable").values())
                        except Exception:
                            already_off = False
                    if not already_off:
                        print(">>> SUPPORT THE ARM: torque is being switched OFF <<<", file=sys.stderr, flush=True)
                        for m in NAMES:
                            ok = False
                            for _ in range(6):
                                try:
                                    bus.write("Torque_Enable", m, 0, normalize=False)
                                    ok = True
                                    break
                                except Exception:
                                    time.sleep(0.01)
                            out["torque_zero_writes"][m] = ok
                    try:
                        out["torque_readback"] = self._read_raw("Torque_Enable")
                    except Exception as e:
                        out["torque_readback"] = f"read failed: {e!r}"
                elif bus is not None:
                    out["note"] = "port not open: no torque was possible from this process"
            finally:
                try:
                    if bus is not None:
                        bus.port_handler.closePort()
                        out["port_closed"] = not bus.port_handler.is_open
                except Exception as e:
                    out["port_closed"] = f"close failed: {e!r}"
                if self._lockfile is not None:
                    try:
                        fcntl.flock(self._lockfile, fcntl.LOCK_UN)
                        self._lockfile.close()
                    except Exception:
                        pass
                    self._lockfile = None
                rb = out["torque_readback"]
                out["torque_off_verified"] = isinstance(rb, dict) and all(v == 0 for v in rb.values())
                if bus is not None and not out["torque_off_verified"] and "note" not in out:
                    out["ALERT"] = "TORQUE OFF NOT CONFIRMED -> CUT THE 12 V POWER NOW"
                    print(out["ALERT"], file=sys.stderr, flush=True)
                self.state = "STOPPED"
                self.bus = None
                self._event("stop", **out)
                if self._log is not None:
                    self._log.close()
                    self._log = None
                self.last_stop = out
            return out

    # ------------------------------------------------------------------ public API
    def get_pose(self):
        with self._lock:
            if self.state not in ("ARMED", "READ_ONLY"):
                raise Refused(f"no live pose in state {self.state}")
            try:
                return self._pose_from_raw(self._read_present())
            except SafetyStop as e:
                self._fault(str(e))
                raise

    def get_camera_frame(self, camera: str = "tool_camera"):
        """One frame, bracketed by two pose reads; moving_during_capture flags any change."""
        import camera as cam
        before = self.get_pose() if self.state in ("ARMED", "READ_ONLY") else None
        frame = cam.capture(camera)
        after = self.get_pose() if self.state in ("ARMED", "READ_ONLY") else None
        moved = None
        if before and after:
            moved = any(abs(after["raw"][m] - before["raw"][m]) > 2 for m in NAMES)
        return {"frame": frame, "pose_before": before, "pose_after": after, "moving_during_capture": moved}

    def hold(self):
        """No new goal. Verifies torque is still ON and returns the pose. Does not extend the watchdog."""
        with self._lock:
            self._require_armed()
            try:
                torque = self._read_raw("Torque_Enable")
                if any(v != 1 for v in torque.values()):
                    raise SafetyStop(f"torque state fault {torque}")
                pose = self._pose_from_raw(self._read_present())
                drift = self._drift(pose["raw"])
                if any(abs(v) > DRIFT_TOL for v in drift.values()):
                    raise SafetyStop(f"drift while holding {drift}")
                return pose
            except SafetyStop as e:
                self._fault(str(e))
                raise

    # ------------------------------------------------------------------ end-effector (official LeRobot kinematics)
    def _kin(self):
        if self._kinematics is None:
            import kinematics
            self._kinematics = kinematics.EEKinematics()
        return self._kinematics

    def get_ee_pose(self):
        """Tool-frame position (mm, URDF base frame) by forward kinematics of the MEASURED joints.
        Works read-only (torque OFF). Accuracy depends on URDF/calibration agreement: UNVERIFIED."""
        pose = self.get_pose()
        return {**self._kin().fk(pose["joints_deg"]), "pose": pose}

    def plan_ee_delta(self, dx_mm: float, dy_mm: float, dz_mm: float):
        """IK plan only: never writes. Says whether the plan would be executable in this session."""
        import kinematics
        for v, n in ((dx_mm, "dx_mm"), (dy_mm, "dy_mm"), (dz_mm, "dz_mm")):
            self._finite(v, n)
        pose = self.get_pose()
        try:
            plan = self._kin().ik_delta(pose["joints_deg"], dx_mm, dy_mm, dz_mm)
        except kinematics.KinematicsError as e:
            raise Refused(f"IK refused: {e}") from None
        reasons = []
        for j, dq in plan["joint_delta_deg"].items():
            if abs(dq) < 0.05:
                continue
            raw = self._to_raw(j, plan["target_joints_deg"][j])
            if j not in self.enabled:
                reasons.append(f"{j} needed ({dq:+.2f} deg) but not enabled")
            if not self._in_limits(j, raw):
                reasons.append(f"{j} target outside calibrated range minus margin")
            if abs(raw - self.session_start_raw[j]) * DEG_PER_COUNT > MAX_EXCURSION_DEG:
                reasons.append(f"{j} would leave the {MAX_EXCURSION_DEG} deg session envelope")
        plan["executable_now"] = False
        plan["blocked_by"] = reasons + ["multi-joint executor not built/commissioned (move_ee_delta disabled)"]
        return plan

    def move_ee_delta(self, dx_mm: float, dy_mm: float, dz_mm: float):
        raise Refused("move_ee_delta is DISABLED: needs a commissioned multi-joint executor and proven "
                      "shoulder_lift / elbow_flex / wrist_flex in both directions (see README_BORIS.md)")

    def set_gripper(self, percent):
        raise GripperDisabled("set_gripper is DISABLED: the gripper holds the drawing tool "
                              "and gripper motion is not proven. Requires a separate HQ GO.")

    def move_joint_delta(self, joint: str, degrees: float):
        with self._lock:
            self._require_armed()
            d = self._finite(degrees, "degrees")
            pose = self.get_pose()
            return self.move_joint_to(joint, pose["joints_deg"][joint] + d, _requested_delta=d)

    def move_joint_to(self, joint: str, target_degrees: float, _requested_delta=None, accept_within_deg=None):
        """accept_within_deg (contact drawing only, <= 1.0): a stall closer than this to the target ends the
        move as reached ("stalled_within") instead of faulting. All other aborts are unchanged."""
        with self._lock:
            self._require_armed()
            if joint not in self.enabled:
                raise Refused(f"joint {joint!r} not enabled in this session (enabled: {self.enabled})")
            target_deg = self._finite(target_degrees, "target_degrees")
            if accept_within_deg is not None and not (0 < self._finite(accept_within_deg, "accept_within_deg") <= 1.0):
                raise Refused("accept_within_deg must be in (0, 1.0]")
            self.last_cmd = time.monotonic()
            try:
                torque = self._read_raw("Torque_Enable")
                if any(v != 1 for v in torque.values()):
                    raise SafetyStop(f"torque state fault {torque}")
                start = self._read_present()
            except SafetyStop as e:
                self._fault(str(e))
                raise
            target_raw = self._to_raw(joint, target_deg)
            excursion = abs(target_raw - self.session_start_raw[joint]) * DEG_PER_COUNT
            need = abs(target_raw - start[joint]) * DEG_PER_COUNT
            remaining = MAX_TRAVEL_DEG - self.travel_deg[joint]
            if not self._in_limits(joint, target_raw):
                raise Refused(f"{joint} target {target_deg:.2f} deg outside calibrated range minus margin")
            if excursion > MAX_EXCURSION_DEG + DEG_PER_COUNT / 2:
                raise Refused(f"{joint} target is {excursion:.2f} deg from session start (max {MAX_EXCURSION_DEG})")
            if need > remaining + DEG_PER_COUNT / 2:
                raise Refused(f"{joint} needs {need:.2f} deg but only {remaining:.2f} deg travel budget left")
            self.state = "EXECUTING"
            res = {"joint": joint, "requested_delta_deg": _requested_delta, "target_deg": round(target_deg, 3),
                   "target_raw": target_raw, "start_deg": round(self._deg(joint, start[joint]), 3),
                   "start_raw": start[joint], "iterations": [], "other_joint_max_drift": {}}
            self._event("move_begin", **{k: v for k, v in res.items() if k != "iterations"})
            try:
                self._execute(joint, target_raw, start, res, accept_within_deg)
            except SafetyStop as e:
                res["fault"] = str(e)
                self._event("move_fault", result=res)
                self._fault(str(e))
                raise SafetyStop(f"{e} -> stopped; result: {json.dumps(res, default=str)}") from None
            except Exception as e:
                self._fault(f"{type(e).__name__}: {e}")
                raise SafetyStop(f"{type(e).__name__}: {e} -> stopped") from None
            except BaseException as e:
                self._fault(f"{type(e).__name__}: {e}")
                raise
            self.state = "ARMED"
            self.last_cmd = time.monotonic()
            self._event("move_end", result=res)
            return res

    # ------------------------------------------------------------------ motion core
    def _execute(self, joint, target_raw, start, res, accept_within_deg=None):
        tol_counts = TOL_DEG / DEG_PER_COUNT
        max_iters = min(40, math.ceil(abs(target_raw - start[joint]) * DEG_PER_COUNT / 0.4) + 5)
        lead_cfg = DEADBAND_LEAD_COUNTS.get(joint, 0)
        lead_pos, lead_neg = lead_cfg if isinstance(lead_cfg, tuple) else (lead_cfg, lead_cfg)
        lo = self.session_start_raw[joint] - MAX_EXCURSION_DEG / DEG_PER_COUNT - 0.5 - lead_neg
        hi = self.session_start_raw[joint] + MAX_EXCURSION_DEG / DEG_PER_COUNT + 0.5 + lead_pos
        if STRICT_SESSION_ENVELOPE:
            radius = math.floor(MAX_EXCURSION_DEG / DEG_PER_COUNT)
            lo, hi = self.session_start_raw[joint] - radius, self.session_start_raw[joint] + radius
        no_prog, cur, worst = 0, start, res["other_joint_max_drift"]   # filled live, kept on faults
        overshot, prev_err = 0, None  # target crossings: the lead halves after each one (no limit cycle)
        for i in range(1, max_iters + 1):
            err = target_raw - cur[joint]
            if abs(err) <= tol_counts:
                break
            if prev_err is not None and (err > 0) != (prev_err > 0):
                overshot += 1
            prev_err = err
            lead = (lead_pos if err > 0 else lead_neg) >> overshot
            lead = lead if err > 0 else -lead
            gap = min(MAX_STEP_COUNTS_JOINT.get(joint, MAX_STEP_COUNTS), max(MAX_STEP_COUNTS, MAX_GAP_CEILING_COUNTS))
            step = max(-gap, min(gap, err + lead))
            goal = cur[joint] + step
            # the lead is an internal overshoot of the goal: shrink it near a limit (the target itself was checked)
            c, mg = self.robot.calibration[joint], LIMIT_MARGIN[joint]
            g_lo, g_hi = max(c.range_min + mg, lo), min(c.range_max - mg, hi)
            if MAX_GOAL_CHANGE_COUNTS is not None:
                previous_goal = self.bus.sync_read("Goal_Position", [joint], normalize=False, num_retry=2)[joint]
                g_lo = max(g_lo, previous_goal - MAX_GOAL_CHANGE_COUNTS, cur[joint] - gap)
                g_hi = min(g_hi, previous_goal + MAX_GOAL_CHANGE_COUNTS, cur[joint] + gap)
                if g_lo > g_hi:
                    raise SafetyStop("No goal satisfies consecutive-command and measured-pose limits")
                goal = min(math.floor(g_hi), max(math.ceil(g_lo), goal))
                step = goal - cur[joint]
            if goal < g_lo and target_raw >= g_lo:
                goal, step = int(math.ceil(g_lo)), int(math.ceil(g_lo)) - cur[joint]
            elif goal > g_hi and target_raw <= g_hi:
                goal, step = int(math.floor(g_hi)), int(math.floor(g_hi)) - cur[joint]
            if not (self._in_limits(joint, goal) and lo <= goal <= hi) or abs(step) > gap:
                raise SafetyStop(f"internal: goal {goal} failed the pre-write check")
            self.bus.sync_write("Goal_Position", {joint: goal}, normalize=False)
            rb = self.bus.sync_read("Goal_Position", [joint], normalize=False, num_retry=2)
            if rb.get(joint) != goal:
                raise SafetyStop(f"Goal_Position readback {rb} != {goal}")
            t_end = time.monotonic() + SETTLE_S
            while True:
                now = self._read_present()
                self._check_sample(joint, now, cur, step, target_raw, worst)
                if time.monotonic() >= t_end:
                    break
                time.sleep(SAMPLE_S)
            moved = now[joint] - cur[joint]
            self.travel_deg[joint] += abs(moved) * DEG_PER_COUNT
            res["iterations"].append({"i": i, "goal_raw": goal, "measured_raw": now[joint],
                                      "measured_deg": round(self._deg(joint, now[joint]), 3),
                                      "moved_counts": moved, "error_deg": round((target_raw - now[joint]) * DEG_PER_COUNT, 3)})
            if self.travel_deg[joint] > MAX_TRAVEL_DEG + OVERSHOOT_TOL_DEG:
                raise SafetyStop(f"{joint} measured travel {self.travel_deg[joint]:.2f} deg exceeds budget")
            no_prog = no_prog + 1 if moved * (1 if step > 0 else -1) < 1 else 0
            cur = now
            if abs(target_raw - cur[joint]) <= tol_counts:
                break
            if no_prog >= NO_PROGRESS_ITERS:
                if accept_within_deg is not None and abs(target_raw - cur[joint]) * DEG_PER_COUNT <= accept_within_deg:
                    res["stalled_within"] = True
                    break
                raise SafetyStop(f"{joint}: no measurable progress over {NO_PROGRESS_ITERS} iterations "
                                 f"(error {(target_raw - cur[joint]) * DEG_PER_COUNT:+.2f} deg)")
        final_err = (target_raw - cur[joint]) * DEG_PER_COUNT
        res.update({"final_deg": round(self._deg(joint, cur[joint]), 3), "final_raw": cur[joint],
                    "final_error_deg": round(final_err, 3), "encoder_counts": cur[joint] - start[joint],
                    "measured_motion_deg": round((cur[joint] - start[joint]) * DEG_PER_COUNT, 3),
                    "reached": abs(final_err) <= TOL_DEG or bool(res.get("stalled_within")), "tolerance_deg": TOL_DEG,
                    "travel_used_deg": round(self.travel_deg[joint], 3)})
        if not res["reached"]:
            raise SafetyStop(f"{joint}: target not reached in {max_iters} iterations (error {final_err:+.2f} deg)")
        self.ref_raw[joint] = cur[joint]

    def _check_sample(self, joint, now, prev, step, target_raw, worst):
        drift = self._drift(now, exclude=joint)
        for k, v in drift.items():
            worst[k] = max(worst.get(k, 0.0), abs(v))
        bad = {k: v for k, v in drift.items() if abs(v) > DRIFT_TOL}
        if bad:
            raise SafetyStop(f"drift on non-moving joints {bad}")
        direction = 1 if step > 0 else -1
        if (now[joint] - prev[joint]) * direction * DEG_PER_COUNT < -REVERSE_TOL_DEG:
            raise SafetyStop(f"{joint} moved opposite to the command ({(now[joint] - prev[joint]) * DEG_PER_COUNT:+.2f} deg)")
        if (now[joint] - target_raw) * direction * DEG_PER_COUNT > OVERSHOOT_TOL_DEG:
            raise SafetyStop(f"{joint} overshoot {(now[joint] - target_raw) * DEG_PER_COUNT:+.2f} deg beyond target")
        if not self._in_limits(joint, now[joint]):
            raise SafetyStop(f"{joint} left its calibrated range minus margin (raw {now[joint]})")

    def _require_armed(self):
        if self.state != "ARMED":
            raise Refused(f"motion refused in state {self.state} (connect(arm=True) after a human GO)")

    @staticmethod
    def _finite(x, name):
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise Refused(f"{name} must be a finite number, got {x!r}")
        return float(x)


# ---------------------------------------------------------------------- module-level API
_ctl: SafeFollower | None = None


def connect(arm: bool = False, joints=None) -> SafeFollower:
    """Open the follower. arm=True switches torque ON: only with a human watching, PSU switch in reach."""
    global _ctl
    if _ctl is not None and _ctl.state not in ("STOPPED", "DISCONNECTED"):
        raise Refused(f"controller already {_ctl.state}")
    _ctl = SafeFollower(joints)
    _ctl.open(arm=arm)
    return _ctl


def _require() -> SafeFollower:
    if _ctl is None:
        raise Refused("call connect() first")
    return _ctl


def get_pose():
    return _require().get_pose()


def get_camera_frame(camera: str = "tool_camera"):
    if _ctl is None:
        import camera as cam
        return {"frame": cam.capture(camera), "pose_before": None, "pose_after": None, "moving_during_capture": None}
    return _ctl.get_camera_frame(camera)


def move_joint_delta(joint: str, degrees: float):
    return _require().move_joint_delta(joint, degrees)


def move_joint_to(joint: str, target_degrees: float):
    return _require().move_joint_to(joint, target_degrees)


def set_gripper(percent: float):
    return _require().set_gripper(percent)


def get_ee_pose():
    return _require().get_ee_pose()


def plan_ee_delta(dx_mm: float, dy_mm: float, dz_mm: float):
    return _require().plan_ee_delta(dx_mm, dy_mm, dz_mm)


def move_ee_delta(dx_mm: float, dy_mm: float, dz_mm: float):
    return _require().move_ee_delta(dx_mm, dy_mm, dz_mm)


def hold():
    return _require().hold()


def stop(reason: str = "requested"):
    return _ctl.stop(reason) if _ctl is not None else None


def _on_signal(signum, frame):
    if _ctl is not None:
        _ctl.stop(f"signal {signum}")
    raise KeyboardInterrupt(f"signal {signum}")


atexit.register(lambda: _ctl.stop("process exit") if _ctl is not None else None)
if threading.current_thread() is threading.main_thread():
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
