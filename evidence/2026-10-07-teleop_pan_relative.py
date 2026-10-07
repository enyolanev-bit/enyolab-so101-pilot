"""Minimal leader -> follower teleop on shoulder_pan ONLY, relative offset (GO HQ 2026-10-07).

follower_target = follower_start + clamp(leader_now - leader_start, -5, +5) degrees.
No absolute pose equality is required. No other joint is commanded (the follower's other joints keep
the goals aligned at startup by the proven sequence and are watched for drift).
Leader: read-only (guarded FeetechMotorsBus, PING/READ only, calibration SHA pinned).
Follower: boris/controller.py proven startup (torque OFF check, Goal := Present, readback, torque ON,
4 s hold), bounded moves (<= 1 deg command gap, 6-count lead), watchdog, verified torque OFF at the end.
Usage: python 2026-10-07-teleop_pan_relative.py --go <out_json> [seconds]
"""
import datetime as dt
import fcntl
import hashlib
import json
import pathlib
import sys
import time

if len(sys.argv) not in (3, 4) or sys.argv[1] != "--go":
    sys.exit("REFUSED: usage --go <out_json> [seconds]")
OUT = pathlib.Path(sys.argv[2])
DURATION = float(sys.argv[3]) if len(sys.argv) == 4 else 40.0
if OUT.exists():
    sys.exit(f"refusing to overwrite {OUT}")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "boris"))
import controller as C  # noqa: E402
import scservo_sdk as scs  # noqa: E402
from serial.tools import list_ports  # noqa: E402
from lerobot.motors import Motor, MotorNormMode, MotorCalibration  # noqa: E402
from lerobot.motors.feetech import FeetechMotorsBus  # noqa: E402

JOINT, CLAMP, DEADZONE = "shoulder_pan", 5.0, 0.5
LEADER_SERIAL = "5B7B015440"
LEADER_CAL = pathlib.Path.home() / ".cache/huggingface/lerobot/calibration/teleoperators/so_leader/pilot001_leader.json"
LEADER_SHA = "974f819f98567cb7c88fb746d389a9424f88a6fc531fb0587343e5285e4c0dae"
NAMES = C.NAMES


class Guard(RuntimeError):
    pass


def open_leader():
    hits = [p.device for p in list_ports.comports() if p.serial_number == LEADER_SERIAL and p.device.startswith("/dev/cu.")]
    if len(hits) != 1:
        raise Guard(f"leader: expected one adapter {LEADER_SERIAL}, found {hits}")
    raw = LEADER_CAL.read_bytes()
    if hashlib.sha256(raw).hexdigest() != LEADER_SHA:
        raise Guard("leader calibration sha mismatch")
    calib = {m: MotorCalibration(**v) for m, v in json.loads(raw).items()}
    lockdir = pathlib.Path.home() / ".cache/enyolab"
    lockdir.mkdir(parents=True, exist_ok=True)
    lock = open(lockdir / f"leader-{LEADER_SERIAL}.lock", "a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    motors = {n: Motor(i, "sts3215", MotorNormMode.RANGE_0_100 if n == "gripper" else MotorNormMode.DEGREES)
              for i, n in enumerate(NAMES, 1)}
    bus = FeetechMotorsBus(port=hits[0], motors=motors, calibration=calib)
    ph = bus.packet_handler
    orig_tx = ph.txPacket

    def tx(port, pkt):                       # leader: PING and READ instructions only
        if pkt[scs.PKT_INSTRUCTION] not in (scs.INST_PING, scs.INST_READ, scs.INST_SYNC_READ):
            raise Guard(f"leader write blocked (instruction {pkt[scs.PKT_INSTRUCTION]})")
        return orig_tx(port, pkt)
    ph.txPacket = tx
    bus.connect(handshake=False)
    if any(bus.ping(i) != 777 for i in range(1, 7)):
        raise Guard("leader ids/models")
    torque = bus.sync_read("Torque_Enable", normalize=False, num_retry=2)
    c = calib[JOINT]
    mid = (c.range_min + c.range_max) / 2
    return bus, lock, (lambda: (bus.sync_read("Present_Position", [JOINT], normalize=False, num_retry=2)[JOINT] - mid) * C.DEG_PER_COUNT), torque


log = {"started": dt.datetime.now().astimezone().isoformat(), "joint": JOINT, "clamp_deg": CLAMP, "samples": [], "moves": 0}
lbus = llock = None
try:
    lbus, llock, leader_deg, ltorque = open_leader()
    log["leader_torque"] = ltorque
    C.MAX_TRAVEL_DEG = 40.0                  # back-and-forth following; excursion stays clamped to +-5 deg
    # Startup bus faults (3 today, all in the alignment write burst, all BEFORE torque ON) -> redo the whole
    # proven startup, at most twice more, only if the failed attempt verified torque OFF on all six servos.
    log["startup_attempts"] = []
    for attempt in range(1, 4):
        try:
            ctl = C.connect(arm=True, joints=[JOINT])
            log["startup_attempts"].append("ok")
            break
        except Exception as e:
            last = C._ctl.last_stop if C._ctl is not None else None
            log["startup_attempts"].append(f"{type(e).__name__}: {str(e)[:160]}")
            if attempt == 3 or not (last and last.get("torque_off_verified")):
                raise
            print(f"startup attempt {attempt} failed before torque (torque OFF verified): retrying", flush=True)
            time.sleep(0.5)
    l0, f0 = leader_deg(), ctl.get_pose()["joints_deg"][JOINT]
    log.update({"leader_start_deg": round(l0, 3), "follower_start_deg": round(f0, 3)})
    print(f"READY: move the LEADER base slowly now ({DURATION:.0f} s window)", flush=True)
    t_end, prev_l = time.monotonic() + DURATION, l0
    while time.monotonic() < t_end:
        l = leader_deg()
        if abs(l - prev_l) > 20:
            raise Guard(f"leader reading jumped {prev_l:.1f} -> {l:.1f} deg")
        prev_l = l
        delta = l - l0
        target = f0 + max(-CLAMP, min(CLAMP, delta))
        fnow = ctl.get_pose()["joints_deg"][JOINT]
        if abs(target - fnow) > DEADZONE:
            ctl.move_joint_to(JOINT, target, accept_within_deg=1.0)
            log["moves"] += 1
            fnow = ctl.get_pose()["joints_deg"][JOINT]
        log["samples"].append({"t": round(time.monotonic(), 2), "leader_delta": round(delta, 2),
                               "target_delta": round(target - f0, 2), "follower_delta": round(fnow - f0, 2)})
        time.sleep(0.1)
    log["result"] = "DONE"
except BaseException as e:
    log["result"], log["error"] = "STOPPED", f"{type(e).__name__}: {e}"[:600]
finally:
    log["stop"] = C.stop("teleop pan test done")
    if lbus is not None:
        try:
            lbus.port_handler.closePort()
        except Exception:
            pass
    if llock is not None:
        fcntl.flock(llock, fcntl.LOCK_UN)
    s = log["samples"]
    if s:
        log["leader_delta_range"] = [min(x["leader_delta"] for x in s), max(x["leader_delta"] for x in s)]
        log["follower_delta_range"] = [min(x["follower_delta"] for x in s), max(x["follower_delta"] for x in s)]
        log["max_tracking_error_deg"] = max(abs(x["follower_delta"] - x["target_delta"]) for x in s)
    with open(OUT, "x") as fh:
        json.dump(log, fh, indent=1, default=str)
    print(json.dumps({k: log.get(k) for k in ("result", "error", "leader_start_deg", "follower_start_deg", "leader_delta_range",
                                               "follower_delta_range", "max_tracking_error_deg", "moves")}, indent=1),
          "\ntorque_off_verified:", (log["stop"] or {}).get("torque_off_verified"), (log["stop"] or {}).get("torque_readback"))
