"""Mouvement AUTONOME VISIBLE du follower SO-101 : 5 pas de +1 degre sur shoulder_pan, sans leader — ENYO-14.

PREPARE pour un GO HQ unique. Ne s'execute qu'avec --go.
Reutilise les briques auditees du lanceur 2026-10-06-first_teleop_launcher.py : garde-fous
statiques (version, empreintes, SHA de calibration, numeros de serie), liste blanche d'ecriture
par adresse, couple a 1 seulement au point autorise, recalage Goal_Position := Present_Position
verifie juste avant l'activation du couple, arret sur (couple a 0 servo par servo, relu).

Sequence :
  1. follower : handshake, IDs 1..6 / 777, couple 0, registres == follower_nevil.json, plages
     (marge 20, wrist_flex 5) ;
  2. configure() avec recalage verifie juste avant enable_torque ;
  3. maintien 4 s : abandon si une position derive de plus de 20 pas ;
  4. 5 PAS successifs : consigne = DERNIERE pose mesuree, shoulder_pan + 1.0 degre ; un send_action
     par pas (max_relative_target = 1.0) ; attente 0,5 s ; relecture ;
  5. a chaque pas : delta shoulder_pan dans [+0,3, +2,0] degres ; autres articulations a +/- 2 de la
     pose de depart (degres, % pour la pince) ; sinon abandon immediat ;
  6. arret sur : couple a 0, relu, port ferme. SOUTENIR LE BRAS.
Aucun leader, aucune camera, aucun dataset.

Relectures groupees de verification (sync_read) : num_retry=2, soit 3 tentatives au maximum
(GO HQ 2026-10-06 apres une erreur isolee « Incorrect status packet »). Aucune relance sur les
ecritures. Echec persistant -> abandon, avant l'activation du couple ou par arret immediat.

Usage : python follower_standalone_5step.py --go <log_prefix>
"""
import sys, json, time, signal, hashlib, inspect, pathlib, datetime, importlib.metadata as md

FOLLOWER_PORT, FOLLOWER_SERIAL = "/dev/cu.usbmodem5B7B0152071", "5B7B015207"
LEADER_PORT, LEADER_SERIAL = "/dev/cu.usbmodem5B7B0154401", "5B7B015440"
FOLLOWER_ID, LEADER_ID = "follower_nevil", "pilot001_leader"
CAL_DIR = pathlib.Path.home() / ".cache/huggingface/lerobot/calibration"
FOLLOWER_CAL_SHA256 = "f48d50d5ba8c220f13575f13c1d6562d9431391fb1e726541abdaf2c4e714a9d"
# Empreinte de la calibration leader APPROUVEE par HQ. Deux versions existent (20:37 5fbbdb26…,
# 22:03 974f819f…), toutes deux TO_REVALIDATE. Tant que HQ n'a pas fixe la valeur : refus.
LEADER_CAL_SHA256 = "974f819f98567cb7c88fb746d389a9424f88a6fc531fb0587343e5285e4c0dae"  # approuve par HQ le 2026-10-06 (GO preuve de vie shoulder_pan)
NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
FPS, MAX_DURATION_S, MAX_REL = 30, 20.0, 1.0
ALIGN_TOL, POST_ENABLE_TOL, LIMIT_MARGIN = 20, 20, 20
# Marge de demarrage par articulation (GO HQ 2026-10-06) : wrist_flex repose par gravite vers 101
# (range_min 91) couple a 0 ; marge reduite a 5 pour wrist_flex seulement, 20 ailleurs.
LIMIT_MARGINS = {m: (5 if m == "wrist_flex" else LIMIT_MARGIN) for m in ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]}
POSE_MATCH_TOL = 5.0
STILL_PHASE_S, STILL_TOL, JUMP_TOL = 4.0, 3.0, 30.0
FOLLOWER_DRIFT_TOL, PAN_LAG_TOL, PAN_LAG_STEPS = 10.0, 15.0, 15
FOLLOWER_ALLOWED = {40, 55, 7, 85, 41, 18, 33, 21, 22, 23, 16, 28, 36, 42}
LEADER_ALLOWED = {40, 55, 7, 85, 41, 18, 33}
AUDITED = {  # sha256[:16] de inspect.getsource, releves sur LeRobot 0.6.1 le 2026-10-06
    "SOFollower.configure": "d56e81dad3cf0688", "SOFollower.send_action": "f90f1700ed2a7b36",
    "SOFollower.get_observation": "6f1ffcd164aacac8", "SOFollower.disconnect": "2ad307b3906d38e4",
    "SOLeader.configure": "078ff2725a40955a", "SOLeader.get_action": "5ab6cc782b965c0b",
    "SOLeader.disconnect": "81389cb0d8536cc2", "SerialMotorsBus.torque_disabled": "c5e45d976557d2aa",
    "SerialMotorsBus.connect": "55089cc557c42960", "SerialMotorsBus.disconnect": "4a977280957c45c4",
    "FeetechMotorsBus.configure_motors": "ff1fdbde15e4aee2", "FeetechMotorsBus.enable_torque": "d6db430cf9fe5780",
    "FeetechMotorsBus.is_calibrated": "614e7db2dc531105", "GroupSyncWrite.txPacket": "0edf16184c94a5ea",
    "ensure_safe_goal_position": "2cd0f6e39b078782", "SerialMotorsBus.write": "94701a0c073db595",
    "SerialMotorsBus._write": "072fe46ea06f5f9f", "SerialMotorsBus.sync_write": "fdd50c8a69fbb538",
    "SerialMotorsBus._unnormalize": "9afda32ddd1a9e0d", "FeetechMotorsBus.disable_torque": "e8d1eb7a1257426d",
    "SerialMotorsBus._normalize": "1821a76bdc3a7287", "SerialMotorsBus.sync_read": "d091ea732675e307",
    "SOFollower.__init__": "b409d9ebc6077dd9", "SOLeader.__init__": "8130f440028ddce1",
    "PPH.writeTxRx": "be0d2d386ac5bc0c", "PPH.syncWriteTxOnly": "b0d8b0b58b629811",
}

if len(sys.argv) != 3 or sys.argv[1] != "--go":
    sys.exit("REFUSED: usage follower_standalone_5step.py --go <log_prefix>  (requires an explicit HQ GO)")
PREFIX = pathlib.Path(sys.argv[2])
EVENTS, STEPS = PREFIX.with_suffix(".events.json"), PREFIX.with_suffix(".steps.jsonl")
for p in (EVENTS, STEPS):
    if p.exists():
        sys.exit(f"ABORT: refusing to overwrite {p}")
if FOLLOWER_SERIAL not in FOLLOWER_PORT or LEADER_SERIAL not in LEADER_PORT:
    sys.exit("ABORT: port/serial mismatch")

from lerobot.robots.so_follower import SO101FollowerConfig, SO101Follower
from lerobot.teleoperators.so_leader import SO101LeaderConfig, SO101Leader
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.teleoperators.so_leader.so_leader import SOLeader
from lerobot.robots.utils import ensure_safe_goal_position
from lerobot.motors.motors_bus import SerialMotorsBus
from lerobot.motors.feetech.feetech import FeetechMotorsBus
import scservo_sdk.group_sync_write as gsw
from scservo_sdk.protocol_packet_handler import protocol_packet_handler as PPH

ev = {"started": datetime.datetime.now().astimezone().isoformat(), "abort": "UNSET (process ended abnormally)",
      "writes": [], "phase": "init", "result": None}
steps_f = open(STEPS, "x")

class Abort(RuntimeError):
    pass

def check_static():
    if md.version("lerobot") != "0.6.1":
        raise Abort(f"lerobot version {md.version('lerobot')} != 0.6.1")
    fns = {"SOFollower.configure": SOFollower.configure, "SOFollower.send_action": SOFollower.send_action,
           "SOFollower.get_observation": SOFollower.get_observation, "SOFollower.disconnect": SOFollower.disconnect,
           "SOLeader.configure": SOLeader.configure, "SOLeader.get_action": SOLeader.get_action,
           "SOLeader.disconnect": SOLeader.disconnect, "SerialMotorsBus.torque_disabled": SerialMotorsBus.torque_disabled,
           "SerialMotorsBus.connect": SerialMotorsBus.connect, "SerialMotorsBus.disconnect": SerialMotorsBus.disconnect,
           "FeetechMotorsBus.configure_motors": FeetechMotorsBus.configure_motors,
           "FeetechMotorsBus.enable_torque": FeetechMotorsBus.enable_torque,
           "FeetechMotorsBus.is_calibrated": FeetechMotorsBus.is_calibrated.fget,
           "GroupSyncWrite.txPacket": gsw.GroupSyncWrite.txPacket,
           "ensure_safe_goal_position": ensure_safe_goal_position, "SerialMotorsBus.write": SerialMotorsBus.write,
           "SerialMotorsBus._write": SerialMotorsBus._write, "SerialMotorsBus.sync_write": SerialMotorsBus.sync_write,
           "SerialMotorsBus._unnormalize": SerialMotorsBus._unnormalize,
           "FeetechMotorsBus.disable_torque": FeetechMotorsBus.disable_torque,
           "SerialMotorsBus._normalize": SerialMotorsBus._normalize, "SerialMotorsBus.sync_read": SerialMotorsBus.sync_read,
           "SOFollower.__init__": SOFollower.__init__, "SOLeader.__init__": SOLeader.__init__,
           "PPH.writeTxRx": PPH.writeTxRx, "PPH.syncWriteTxOnly": PPH.syncWriteTxOnly}
    for k, f in fns.items():
        h = hashlib.sha256(inspect.getsource(f).encode()).hexdigest()[:16]
        if h != AUDITED[k]:
            raise Abort(f"source of {k} changed since audit ({h} != {AUDITED[k]})")
    for path, want in ((CAL_DIR / "robots/so_follower" / f"{FOLLOWER_ID}.json", FOLLOWER_CAL_SHA256),):
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        if got != want:
            raise Abort(f"calibration file {path.name} sha256 {got[:12]}… != pinned {want[:12]}…")

state = {"follower_torque_on_allowed": False}

def install_write_guard(bus, who, allowed):
    ph = bus.packet_handler
    orig_w, orig_s = ph.writeTxRx, ph.syncWriteTxOnly
    def writeTxRx(port, scs_id, address, length, data):
        val = data[0] if length == 1 else (data[0] | (data[1] << 8))
        ev["writes"].append({"t": round(time.monotonic(), 3), "who": who, "phase": ev["phase"], "kind": "write",
                             "id": scs_id, "addr": address, "value": val})
        if address not in allowed:
            raise Abort(f"{who}: write to forbidden address {address} (id {scs_id})")
        if address == 40:
            if val == 1 and not (who == "follower" and state["follower_torque_on_allowed"]):
                raise Abort(f"{who}: Torque_Enable=1 outside the authorized point (id {scs_id})")
            if val not in (0, 1):
                raise Abort(f"{who}: Torque_Enable={val} forbidden (id {scs_id})")
        return orig_w(port, scs_id, address, length, data)
    def syncWriteTxOnly(port, start_address, data_length, param, param_length):
        ev["writes"].append({"t": round(time.monotonic(), 3), "who": who, "phase": ev["phase"], "kind": "sync_write",
                             "addr": start_address, "n": param_length // (data_length + 1)})
        if start_address not in allowed or start_address == 40:
            raise Abort(f"{who}: sync_write to forbidden address {start_address}")
        return orig_s(port, start_address, data_length, param, param_length)
    ph.writeTxRx, ph.syncWriteTxOnly = writeTxRx, syncWriteTxOnly
    for m in ("writeTxOnly", "write1ByteTxOnly", "write2ByteTxOnly", "write4ByteTxOnly",
              "regWriteTxOnly", "regWriteTxRx", "action"):
        setattr(ph, m, lambda *a, _m=m, **k: (_ for _ in ()).throw(Abort(f"{who}: {_m} forbidden")))

def circ(a, b):
    d = abs(a - b) % 4096
    return min(d, 4096 - d)

def precheck_bus(dev, who):
    bus = dev.bus
    bus.connect()                                 # handshake : ping 1..6 + firmware (lecture)
    ids = {i: bus.ping(i) for i in range(1, 7)}
    if any(v != 777 for v in ids.values()):
        raise Abort(f"{who}: ids/models {ids}")
    torque = bus.sync_read("Torque_Enable", normalize=False, num_retry=2)
    if any(v != 0 for v in torque.values()):
        raise Abort(f"{who}: torque not 0 at start {torque}")
    if not dev.is_calibrated:                     # registres == fichier (lecture)
        raise Abort(f"{who}: calibration registers != {dev.id}.json")
    ev[f"{who}_precheck"] = {"ids": ids, "torque": torque}

def log_step(row):
    steps_f.write(json.dumps(row) + "\n")
    steps_f.flush()

def safe_shutdown(dev, who):
    """Couple a 0 servo par servo (chaque ecriture isolee), relecture, fermeture. Jamais d'exception."""
    out = {"torque_zero_writes": {}, "torque_readback": None}
    if dev is None:
        return out
    bus = dev.bus
    if who == "follower":
        try:
            print(">>> SOUTENIR LE BRAS FOLLOWER : couple coupe maintenant, il peut retomber <<<", file=sys.stderr, flush=True)
        except Exception:
            pass
    if not bus.is_connected:
        out["note"] = "port never opened or already closed: no torque possible from this process"
        return out
    try:
        try:
            bus.port_handler.clearPort()
            bus.port_handler.is_using = False
        except Exception:
            pass
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
            out["torque_readback"] = bus.sync_read("Torque_Enable", normalize=False, num_retry=2)
        except Exception as e:
            out["torque_readback"] = f"read failed: {e!r}"
    finally:
        try:
            bus.port_handler.closePort()
            out["port_closed"] = not bus.port_handler.is_open
        except Exception as e:
            out["port_closed"] = f"close failed: {e!r}"
    rb = out["torque_readback"]
    if not (isinstance(rb, dict) and all(v == 0 for v in rb.values())):
        out["ALERT"] = f"{who}: TORQUE NOT CONFIRMED 0 -> CUT THE 12 V POWER NOW"
        try:
            print(out["ALERT"], file=sys.stderr, flush=True)
        except Exception:
            pass
    return out


STEP_DEG, HOLD_S, SETTLE_S, N_STEPS = 1.0, 4.0, 0.5, 5
PAN_MIN, PAN_MAX, OTHER_TOL = 0.3, 2.0, 2.0
robot = None
teleop = None
try:
    check_static()
    robot = SO101Follower(SO101FollowerConfig(port=FOLLOWER_PORT, id=FOLLOWER_ID, max_relative_target=MAX_REL, use_degrees=True))
    install_write_guard(robot.bus, "follower", FOLLOWER_ALLOWED)
    rb = robot.bus

    ev["phase"] = "follower_precheck"
    precheck_bus(robot, "follower")
    p0 = rb.sync_read("Present_Position", normalize=False, num_retry=2)
    ev["initial_raw"] = p0
    ev["follower_registers_before"] = {r: rb.sync_read(r, normalize=False, num_retry=2)
                                       for r in ("Goal_Position", "Goal_Time", "Goal_Velocity", "Torque_Limit")}
    for m in NAMES:
        c, mg = robot.calibration[m], LIMIT_MARGINS[m]
        if not (c.range_min + mg <= p0[m] <= c.range_max - mg):
            raise Abort(f"follower {m} present {p0[m]} outside [{c.range_min}+{mg}, {c.range_max}-{mg}]")

    orig_enable = rb.enable_torque
    def aligned_enable_torque(motors=None, num_retry=0):
        if sys.exc_info()[0] is not None:
            raise Abort(f"configure() failed ({sys.exc_info()[0].__name__}) -> refusing torque enable")
        ev["phase"] = "follower_goal_alignment"
        present = rb.sync_read("Present_Position", normalize=False, num_retry=2)
        for m, v in present.items():
            rb.write("Goal_Position", m, v, normalize=False)
        goal = rb.sync_read("Goal_Position", normalize=False, num_retry=2)
        present2 = rb.sync_read("Present_Position", normalize=False, num_retry=2)
        check = {m: {"written": present[m], "goal_readback": goal[m], "present_now": present2[m],
                     "moved_since_precheck": circ(present2[m], p0[m])} for m in present}
        ev["follower_goal_alignment"] = check
        bad = {m: c for m, c in check.items() if c["goal_readback"] != c["written"] or c["moved_since_precheck"] > ALIGN_TOL
               or not (robot.calibration[m].range_min + LIMIT_MARGINS[m] <= c["present_now"] <= robot.calibration[m].range_max - LIMIT_MARGINS[m])}
        if bad:
            raise Abort(f"goal alignment failed {bad}")
        ev["phase"] = "follower_torque_enable"
        state["follower_torque_on_allowed"] = True
        try:
            orig_enable(motors, num_retry)
        finally:
            state["follower_torque_on_allowed"] = False
        ev["torque_enabled_at"] = datetime.datetime.now().astimezone().isoformat()
        ev["follower_aligned_positions"] = present2
    rb.enable_torque = aligned_enable_torque
    ev["phase"] = "follower_configure"
    robot.configure()
    rb.enable_torque = orig_enable

    ev["phase"] = "hold_4s"
    ref = ev["follower_aligned_positions"]
    t_end, max_drift = time.monotonic() + HOLD_S, {m: 0 for m in NAMES}
    while time.monotonic() < t_end:
        cur = rb.sync_read("Present_Position", normalize=False, num_retry=2)
        for m in cur:
            max_drift[m] = max(max_drift[m], circ(cur[m], ref[m]))
        log_step({"t": round(time.monotonic(), 3), "phase": "hold", "raw": cur})
        if any(d > POST_ENABLE_TOL for d in max_drift.values()):
            raise Abort(f"unexpected motion during hold {max_drift}")
        time.sleep(0.05)
    ev["hold_max_drift_raw"] = max_drift

    ev["phase"] = "multi_step"
    obs_start = robot.get_observation()
    ev["obs_start"] = obs_start
    ev["steps"] = []
    for i in range(1, N_STEPS + 1):
        obs_prev = robot.get_observation()
        raw_prev = rb.sync_read("Present_Position", normalize=False, num_retry=2)["shoulder_pan"]
        target = dict(obs_prev)
        target["shoulder_pan.pos"] = obs_prev["shoulder_pan.pos"] + STEP_DEG
        sent = robot.send_action(target)          # un envoi par pas, borne max_relative_target = 1.0
        t_end = time.monotonic() + SETTLE_S
        while time.monotonic() < t_end:
            log_step({"t": round(time.monotonic(), 3), "phase": f"step{i}", "obs": robot.get_observation()})
            time.sleep(0.05)
        obs_now = robot.get_observation()
        raw_now = rb.sync_read("Present_Position", normalize=False, num_retry=2)["shoulder_pan"]
        d = obs_now["shoulder_pan.pos"] - obs_prev["shoulder_pan.pos"]
        drift = {k: round(obs_now[k] - obs_start[k], 3) for k in obs_start if k != "shoulder_pan.pos"}
        rec = {"step": i, "requested_target_deg": round(target["shoulder_pan.pos"], 3), "sent_deg": round(sent["shoulder_pan.pos"], 3),
               "measured_before_deg": round(obs_prev["shoulder_pan.pos"], 3), "measured_after_deg": round(obs_now["shoulder_pan.pos"], 3),
               "delta_deg": round(d, 3), "raw_before": raw_prev, "raw_after": raw_now, "encoder_counts": raw_now - raw_prev,
               "other_joint_drift_from_start": drift}
        ev["steps"].append(rec)
        if not (PAN_MIN <= d <= PAN_MAX):
            raise Abort(f"step {i}: shoulder_pan moved {d:+.3f} deg, expected +{PAN_MIN}..+{PAN_MAX}")
        bad = {k: v for k, v in drift.items() if abs(v) > OTHER_TOL}
        if bad:
            raise Abort(f"step {i}: non-shoulder_pan drift beyond {OTHER_TOL}: {bad}")
    obs_end = robot.get_observation()
    ev["obs_end"] = obs_end
    ev["total_shoulder_pan_deg"] = round(obs_end["shoulder_pan.pos"] - obs_start["shoulder_pan.pos"], 3)
    ev["total_encoder_counts"] = sum(s["encoder_counts"] for s in ev["steps"])
    ev["other_joint_drift_total"] = {k: round(obs_end[k] - obs_start[k], 3) for k in obs_start if k != "shoulder_pan.pos"}
    ev["phase"] = "done"
    ev["abort"] = None
except Abort as e:
    ev["abort"] = f"ABORT[{ev['phase']}]: {e}"
except KeyboardInterrupt:
    ev["abort"] = f"KeyboardInterrupt[{ev['phase']}]"
except BaseException as e:
    ev["abort"] = f"{type(e).__name__}[{ev['phase']}]: {e}"
finally:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    ev["shutdown"] = {"follower": safe_shutdown(robot, "follower")}
    steps_f.close()
    ev["result"] = "PASS" if ev["abort"] is None and ev["shutdown"]["follower"].get("torque_readback") and \
        isinstance(ev["shutdown"]["follower"]["torque_readback"], dict) and \
        all(v == 0 for v in ev["shutdown"]["follower"]["torque_readback"].values()) else "BLOCKED"
    ev["finished"] = datetime.datetime.now().astimezone().isoformat()
    out_path = EVENTS if not EVENTS.exists() else EVENTS.with_name(EVENTS.stem + f".{int(time.time())}.json")
    with open(out_path, "x") as f:
        json.dump(ev, f, indent=1, default=str)
    print(json.dumps({k: ev.get(k) for k in ("result", "abort", "hold_max_drift_raw", "steps", "total_shoulder_pan_deg",
                                               "total_encoder_counts", "other_joint_drift_total", "shutdown")}, indent=1, default=str))
