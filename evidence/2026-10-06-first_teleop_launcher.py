"""Lanceur de la PREMIERE teleoperation SO-101 (leader -> follower) — ENYO-14 — v2 (apres revue).

PREPARE, NON EXECUTE. Ne s'execute qu'avec --go (GO HQ explicite pour CETTE session).
Ne debloque pas scripts/teleop.sh, qui reste bloque.

Risque traite : `Goal_Position` perime. Le follower lisait Goal_Position = 0 sur les 6 servos
(2026-10-06 22:20), et SOFollower.configure() reactive le couple (torque_disabled -> finally
enable_torque) AVANT la premiere consigne bornee. Le recalage Goal_Position := Present_Position,
puis sa verification, est insere JUSTE AVANT l'activation du couple, en remplacant
robot.bus.enable_torque. Si le recalage echoue, ou si configure() a echoue, l'exception
empeche l'activation du couple.

Sequence :
  0. garde-fous statiques : lerobot == 0.6.1 ; empreintes du code audite ; ports verifies par
     numero de serie ; refus d'ecraser le journal ; SHA-256 des DEUX fichiers de calibration
     epingles (le leader doit etre fixe par HQ : LEADER_CAL_SHA256, sinon refus).
  1. FOLLOWER : bus.connect() (handshake, lecture) ; IDs 1..6 / modele 777 ; Torque_Enable == 0 ;
     is_calibrated (registres == follower_nevil.json) ; journalise Goal/Present, Goal_Time,
     Goal_Velocity, Torque_Limit.
  2. FOLLOWER : position presente dans [range_min+20, range_max-20] pour chaque servo.
  3. FOLLOWER : robot.configure(). Juste avant l'activation du couple :
        a. refus si configure() a leve une exception (sys.exc_info) ;
        b. lire Present_Position ; ecrire Goal_Position := Present_Position ;
        c. relire : Goal_Position == valeur ecrite EXACTEMENT ; |Present - Present du precheck| <= 20 ;
           Present toujours dans [range_min+20, range_max-20] ;
        d. seulement alors : enable_torque().
  4. FOLLOWER : 0,5 s apres l'activation, abandon si une position derive de plus de 20.
  5. LEADER : bus.connect() ; IDs 1..6 ; Torque_Enable == 0 ; is_calibrated
     (== pilot001_leader.json) ; teleop.configure() (couple leader = 0, jamais active).
  6. CONCORDANCE DES POSES, avant toute consigne : |follower - leader| <= 5 (degres ; % pour la
     pince) sur chaque articulation. Sinon abandon : pas de rattrapage multi-articulations.
  7. Boucle : fps = 30, duree <= 20 s, max_relative_target = 1.0.
        - 4 premieres s : AUCUNE consigne envoyee (le follower tient sa position recalee) ;
          abandon si le leader s'ecarte de plus de 3 sur une articulation.
        - ensuite : consignes envoyees ; seul shoulder_pan peut s'ecarter de plus de 3 ;
        - abandon si le leader saute de plus de 30 en un pas (franchissement 0/4095) ;
        - abandon si une articulation du follower autre que shoulder_pan s'ecarte de plus de 10
          de sa pose initiale ;
        - abandon si |follower - derniere consigne| > 5 (deplacement brusque) ;
        - abandon si shoulder_pan du follower retarde de plus de 10 sur le leader pendant 15 pas
          (0,5 s), signe d'un blocage ou d'une non-reponse.
     SIGINT est ignore pendant l'arret : un arret bloque se coupe par le 12 V (ou SIGTERM).
  8. Arret : FOLLOWER d'abord. Couple a 0 servo par servo (tolerant aux erreurs), relecture de
     Torque_Enable, fermeture du port ; puis leader. Si un couple n'est pas confirme a 0 :
     message COUPER LE 12 V. SOUTENIR LE BRAS FOLLOWER (couple a 0 = il retombe).

Ecritures autorisees, liste blanche par ADRESSE, toute autre -> abandon :
  follower : 40 Torque_Enable, 55 Lock, 7, 85, 41, 18, 33, 21/22/23, 16, 28, 36, 42 Goal_Position
  leader   : 40, 55, 7, 85, 41, 18, 33
  Torque_Enable (40) : seule la valeur 0 est acceptee ; la valeur 1 uniquement sur le follower au
  point 3d. Toute autre valeur est refusee (ex. 128 = recentrage d'offset sur STS).

Usage : python first_teleop_launcher.py --go <log_prefix>
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
    sys.exit("REFUSED: usage first_teleop_launcher.py --go <log_prefix>  (requires an explicit HQ GO)")
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
    if LEADER_CAL_SHA256 is None:
        raise Abort("leader calibration not approved by HQ (LEADER_CAL_SHA256 is None)")
    for path, want in ((CAL_DIR / "robots/so_follower" / f"{FOLLOWER_ID}.json", FOLLOWER_CAL_SHA256),
                       (CAL_DIR / "teleoperators/so_leader" / f"{LEADER_ID}.json", LEADER_CAL_SHA256)):
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
    torque = bus.sync_read("Torque_Enable", normalize=False)
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
            out["torque_readback"] = bus.sync_read("Torque_Enable", normalize=False)
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

robot = teleop = None
try:
    check_static()
    robot = SO101Follower(SO101FollowerConfig(port=FOLLOWER_PORT, id=FOLLOWER_ID, max_relative_target=MAX_REL, use_degrees=True))
    teleop = SO101Leader(SO101LeaderConfig(port=LEADER_PORT, id=LEADER_ID, use_degrees=True))
    install_write_guard(robot.bus, "follower", FOLLOWER_ALLOWED)
    install_write_guard(teleop.bus, "leader", LEADER_ALLOWED)

    # 1-2. FOLLOWER : verifications en lecture
    ev["phase"] = "follower_precheck"
    precheck_bus(robot, "follower")
    rb = robot.bus
    p0 = rb.sync_read("Present_Position", normalize=False)
    ev["follower_registers_before"] = {r: rb.sync_read(r, normalize=False)
                                       for r in ("Goal_Position", "Goal_Time", "Goal_Velocity", "Torque_Limit")}
    for m in NAMES:
        c = robot.calibration[m]
        mg = LIMIT_MARGINS[m]
        if not (c.range_min + mg <= p0[m] <= c.range_max - mg):
            raise Abort(f"follower {m} present {p0[m]} outside [{c.range_min}+{mg}, {c.range_max}-{mg}]")

    # 3. FOLLOWER : configure() avec recalage juste avant l'activation du couple
    orig_enable = rb.enable_torque
    def aligned_enable_torque(motors=None, num_retry=0):
        if sys.exc_info()[0] is not None:
            raise Abort(f"configure() failed ({sys.exc_info()[0].__name__}) -> refusing torque enable")
        ev["phase"] = "follower_goal_alignment"
        present = rb.sync_read("Present_Position", normalize=False)
        for m, v in present.items():
            rb.write("Goal_Position", m, v, normalize=False)
        goal = rb.sync_read("Goal_Position", normalize=False)
        present2 = rb.sync_read("Present_Position", normalize=False)
        check = {m: {"written": present[m], "goal_readback": goal[m], "present_now": present2[m],
                     "moved_since_precheck": circ(present2[m], p0[m])} for m in present}
        ev["follower_goal_alignment"] = check
        bad = {m: c for m, c in check.items() if c["goal_readback"] != c["written"] or c["moved_since_precheck"] > ALIGN_TOL
               or not (robot.calibration[m].range_min + LIMIT_MARGINS[m] <= c["present_now"] <= robot.calibration[m].range_max - LIMIT_MARGINS[m])}
        if bad:
            raise Abort(f"goal alignment failed {bad}")        # couple jamais active
        ev["phase"] = "follower_torque_enable"
        state["follower_torque_on_allowed"] = True
        try:
            orig_enable(motors, num_retry)
        finally:
            state["follower_torque_on_allowed"] = False
        ev["follower_aligned_positions"] = present2
    rb.enable_torque = aligned_enable_torque
    ev["phase"] = "follower_configure"
    robot.configure()
    rb.enable_torque = orig_enable

    # 4. FOLLOWER : stabilite apres activation du couple
    ev["phase"] = "follower_post_enable"
    ref = ev["follower_aligned_positions"]
    t_end, drift = time.monotonic() + 0.5, {}
    while time.monotonic() < t_end:
        cur = rb.sync_read("Present_Position", normalize=False)
        drift = {m: circ(cur[m], ref[m]) for m in cur}
        if any(d > POST_ENABLE_TOL for d in drift.values()):
            raise Abort(f"follower moved after torque enable {drift}")
        time.sleep(0.05)
    ev["follower_post_enable_drift"] = drift

    # 5. LEADER
    ev["phase"] = "leader_precheck"
    precheck_bus(teleop, "leader")
    ev["phase"] = "leader_configure"
    teleop.configure()                           # couple leader = 0 ; jamais active

    # 6. Concordance des poses avant toute consigne
    ev["phase"] = "pose_match"
    f0 = robot.get_observation()
    a0 = teleop.get_action()
    mismatch = {k: round(f0[k] - a0[k], 2) for k in a0 if abs(f0[k] - a0[k]) > POSE_MATCH_TOL}
    ev["pose_match"] = {"follower": f0, "leader": a0, "mismatch": mismatch}
    if mismatch:
        raise Abort(f"leader/follower poses differ by > {POSE_MATCH_TOL}: {mismatch}")

    # 7. Boucle bornee
    ev["phase"] = "teleop_loop"
    prev, start, track_bad = dict(a0), time.monotonic(), 0
    last_sent = None
    while time.monotonic() - start < MAX_DURATION_S:
        t0 = time.monotonic()
        obs = robot.get_observation()
        act = teleop.get_action()
        el = t0 - start
        for k, v in act.items():
            if abs(v - prev[k]) > JUMP_TOL:
                raise Abort(f"leader jump on {k}: {prev[k]:.1f} -> {v:.1f} (possible 0/4095 wrap)")
            if abs(v - a0[k]) > STILL_TOL and (el < STILL_PHASE_S or k != "shoulder_pan.pos"):
                raise Abort(f"protocol: leader {k} moved {v - a0[k]:+.1f} at t={el:.2f}s")
        for k, v in obs.items():
            if k != "shoulder_pan.pos" and abs(v - f0[k]) > FOLLOWER_DRIFT_TOL:
                raise Abort(f"follower {k} drifted {v - f0[k]:+.1f} from initial pose")
        if last_sent is not None and any(abs(obs[k] - last_sent[k]) > 5.0 for k in last_sent):
            raise Abort(f"follower sudden displacement vs last command: obs={obs} sent={last_sent}")
        if el >= STILL_PHASE_S and abs(obs["shoulder_pan.pos"] - act["shoulder_pan.pos"]) > PAN_LAG_TOL:
            track_bad += 1
            if track_bad >= PAN_LAG_STEPS:
                raise Abort(f"follower shoulder_pan not following leader (lag > {PAN_LAG_TOL} for {PAN_LAG_STEPS} steps)")
        else:
            track_bad = 0
        sent = None
        if el >= STILL_PHASE_S:
            sent = robot.send_action(act)        # borne max_relative_target = 1.0
            last_sent = sent
        log_step({"t": round(el, 3), "obs": obs, "leader": act, "sent": sent})
        prev = act
        time.sleep(max(0.0, 1 / FPS - (time.monotonic() - t0)))
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
    ev["shutdown"] = {"follower": safe_shutdown(robot, "follower"), "leader": safe_shutdown(teleop, "leader")}
    steps_f.close()
    ev["result"] = "COMPLETED" if ev["abort"] is None else "ABORTED"
    ev["finished"] = datetime.datetime.now().astimezone().isoformat()
    out_path = EVENTS if not EVENTS.exists() else EVENTS.with_name(EVENTS.stem + f".{int(time.time())}.json")
    with open(out_path, "x") as f:
        json.dump(ev, f, indent=1, default=str)
    print(json.dumps({k: ev.get(k) for k in ("result", "abort", "shutdown")}, indent=1, default=str))
