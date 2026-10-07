"""Sonde v2 — LEADER — detection de franchissement 0/4095 — LECTURE SEULE (ENYO-14).

Chemin audite (LeRobot 0.6.1) : FeetechMotorsBus direct ; connect(handshake=False) ;
broadcast_ping + ping ; read(normalize=False) ; port_handler.closePort().
Gardes : toute methode d'ecriture leve une exception ; chaque paquet est journalise
et refuse si l'instruction n'est pas PING (1) ou READ (2).
v2 : refuse d'ecraser un fichier ; journal JSONL ecrit au fil de l'eau ; resume ecrit
dans finally (y compris Ctrl+C / SIGTERM) ; port verifie par numero de serie USB.

Usage : python leader_wrap_probe.py <port> <out_prefix> <control_file>
Phases pilotees par l'operateur en ecrivant dans <control_file> : ID2, ID3, ID4, STOP.
"""
import json, sys, time, signal, pathlib, datetime
import scservo_sdk as scs
from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus

PORT, PREFIX, CTL = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
EXPECTED_SERIAL = "5B7B015440"          # adaptateur leader (identification du 2026-10-05)
NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
WATCH = {2: "shoulder_lift", 3: "elbow_flex", 4: "wrist_flex"}
PERIOD_S, MAX_RUN_S, WRAP_DELTA = 0.02, 900.0, 2048
MAX_GAP_S = 0.1          # au-dela, l'echantillon precedent n'est pas comparable (lecture bloquee)
MIN_TRAVEL = 200         # course minimale observee pour qu'une phase compte comme parcourue
ALLOWED_INST = {scs.INST_PING: "PING", scs.INST_READ: "READ"}
EEPROM_REGS = ["Homing_Offset", "Min_Position_Limit", "Max_Position_Limit", "Phase"]

if EXPECTED_SERIAL not in PORT:
    sys.exit(f"ABORT: port {PORT} does not carry leader serial {EXPECTED_SERIAL}")
SAMPLES = PREFIX.with_suffix(".samples.jsonl")
SUMMARY = PREFIX.with_suffix(".json")
for p in (SAMPLES, SUMMARY):
    if p.exists():
        sys.exit(f"ABORT: refusing to overwrite {p}")
if CTL.exists() and CTL.read_text().strip():
    sys.exit(f"ABORT: control file {CTL} not empty at start (stale phase)")
samples_f = open(SAMPLES, "x")

log = {"started": datetime.datetime.now().astimezone().isoformat(), "port": PORT,
       "method": "FeetechMotorsBus direct; connect(handshake=False); broadcast_ping; ping; "
                 "read(normalize=False); port_handler.closePort()",
       "tx_counts": {}, "write_calls": 0, "blocked_calls": [], "comm_errors": [], "abort": None}

class WriteGuard(RuntimeError):
    pass

def guard(name):
    def _blocked(*a, **k):
        log["write_calls"] += 1
        log["blocked_calls"].append(name)
        raise WriteGuard(f"write path reached: {name}")
    return _blocked

def _sigterm(signum, frame):
    raise KeyboardInterrupt(f"signal {signum}")
signal.signal(signal.SIGTERM, _sigterm)

bus = FeetechMotorsBus(port=PORT, calibration=None,
                       motors={n: Motor(i, "sts3215", MotorNormMode.RANGE_M100_100) for i, n in enumerate(NAMES, 1)})
for m in ("write", "sync_write", "_write", "_sync_write", "enable_torque", "disable_torque",
          "_disable_torque", "write_calibration", "reset_calibration", "configure_motors",
          "setup_motor", "set_half_turn_homings", "disconnect"):
    setattr(bus, m, guard(f"bus.{m}"))
ph = bus.packet_handler
for m in ("writeTxOnly", "writeTxRx", "write1ByteTxOnly", "write1ByteTxRx", "write2ByteTxOnly",
          "write2ByteTxRx", "write4ByteTxOnly", "write4ByteTxRx", "regWriteTxOnly", "regWriteTxRx",
          "syncWriteTxOnly", "action"):
    setattr(ph, m, guard(f"packet_handler.{m}"))
_orig_tx = ph.txPacket
def _tx(port, txpacket):
    inst = txpacket[scs.PKT_INSTRUCTION]
    key = ALLOWED_INST.get(inst, f"FORBIDDEN_{inst}")
    log["tx_counts"][key] = log["tx_counts"].get(key, 0) + 1
    if inst not in ALLOWED_INST:
        log["write_calls"] += 1
        raise WriteGuard(f"forbidden instruction {inst}")
    return _orig_tx(port, txpacket)
ph.txPacket = _tx

def read_phase():
    try:
        v = CTL.read_text().strip().upper()
        return v if v in ("ID2", "ID3", "ID4", "STOP") else None
    except FileNotFoundError:
        return None

stats = {}   # (phase, id) -> dict
def upd(phase, id_, t, pos):
    s = stats.setdefault(f"{phase}/{id_}", {"n": 0, "min": None, "max": None, "first": None, "last": None,
                                            "max_abs_delta": 0, "wraps": [], "gap_resets": 0})
    if s["last"] is not None and (t - s["last"][0]) > MAX_GAP_S:
        s["gap_resets"] += 1          # trou de lecture : pas de comparaison a travers le trou
    elif s["last"] is not None:
        d = pos - s["last"][1]
        if abs(d) > s["max_abs_delta"]:
            s["max_abs_delta"] = abs(d)
        if abs(d) > WRAP_DELTA:
            s["wraps"].append({"t": t, "dt": round(t - s["last"][0], 3), "from": s["last"][1], "to": pos, "delta": d})
    s["n"] += 1
    s["min"] = pos if s["min"] is None else min(s["min"], pos)
    s["max"] = pos if s["max"] is None else max(s["max"], pos)
    if s["first"] is None:
        s["first"] = pos
    s["last"] = (t, pos)

try:
    bus.connect(handshake=False)
    bp = bus.broadcast_ping()
    per_id = {i: bus.ping(i) for i in range(1, 7)}
    log["broadcast_ping"] = bp
    log["ping"] = per_id
    if sorted(bp or {}) != [1, 2, 3, 4, 5, 6] or any(per_id[i] != 777 for i in per_id):
        raise RuntimeError("DISCOVERY: ids/models != expected")
    log["eeprom_regs"] = {i: {r: bus.read(r, n, normalize=False) for r in EEPROM_REGS}
                          for i, n in enumerate(NAMES, 1)}
    log["torque_start"] = {i: bus.read("Torque_Enable", n, normalize=False) for i, n in enumerate(NAMES, 1)}

    t0 = time.monotonic()
    phase = None
    while time.monotonic() - t0 < MAX_RUN_S:
        new = read_phase()
        if new and new != phase:
            phase = new
            samples_f.write(json.dumps({"t": round(time.monotonic() - t0, 3), "phase": phase}) + "\n")
            samples_f.flush()
        if phase == "STOP":
            break
        if phase is None:
            time.sleep(0.1)
            continue
        tick = time.monotonic()
        row = {"t": round(tick - t0, 3), "phase": phase}
        for id_, name in WATCH.items():
            try:
                pos = bus.read("Present_Position", name, normalize=False)
                row[str(id_)] = pos
                upd(phase, id_, row["t"], pos)
            except WriteGuard:
                raise
            except Exception as e:
                row[str(id_)] = None
                log["comm_errors"].append({"t": row["t"], "id": id_, "err": f"{type(e).__name__}: {e}"[:200]})
        samples_f.write(json.dumps(row) + "\n")
        samples_f.flush()
        time.sleep(max(0.0, PERIOD_S - (time.monotonic() - tick)))
    else:
        log["abort"] = f"timeout {MAX_RUN_S}s without STOP"
    log["torque_end"] = {i: bus.read("Torque_Enable", n, normalize=False) for i, n in enumerate(NAMES, 1)}
except WriteGuard as e:
    log["abort"] = f"WRITE GUARD: {e}"
except KeyboardInterrupt as e:
    log["abort"] = f"interrupted: {e}"
except Exception as e:
    log["abort"] = f"{type(e).__name__}: {e}"
finally:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    try:
        ser = getattr(bus.port_handler, "ser", None)
        if bus.port_handler.is_open or (ser is not None and ser.is_open):
            bus.port_handler.closePort()
        log["port_closed"] = not bus.port_handler.is_open
    except Exception as e:
        log["port_closed"] = False
        log["close_error"] = repr(e)
    log["close_path"] = "bus.port_handler.closePort() (direct; disconnect() NOT called)"
    samples_f.close()
    for k, s in stats.items():
        s["last"] = s["last"][1] if s["last"] else None
    log["stats"] = stats
    per_joint = {}
    for id_ in WATCH:
        s = stats.get(f"ID{id_}/{id_}")
        per_joint[id_] = None if s is None else {
            "observed_range": [s["min"], s["max"]], "max_abs_delta": s["max_abs_delta"],
            "wrap": bool(s["wraps"]), "samples": s["n"], "gap_resets": s["gap_resets"],
            "travel": s["max"] - s["min"], "travelled": (s["max"] - s["min"]) >= MIN_TRAVEL}
    log["per_joint_own_phase"] = per_joint
    torque_changed = log.get("torque_start") != log.get("torque_end") if "torque_end" in log else None
    log["torque_changed"] = torque_changed
    ok = (log["abort"] is None and log["write_calls"] == 0 and not log["comm_errors"]
          and log.get("port_closed") and torque_changed is False
          and all(v is not None and v["travelled"] for v in per_joint.values()))
    if any(v and v["wrap"] for v in per_joint.values()):
        log["result"] = "FAIL_WRAP"
    else:
        log["result"] = "PASS" if ok else "BLOCKED"
    log["finished"] = datetime.datetime.now().astimezone().isoformat()
    with open(SUMMARY, "x") as f:
        json.dump(log, f, indent=1, default=str)
    print(json.dumps({k: log.get(k) for k in ("result", "abort", "write_calls", "port_closed",
                                               "tx_counts", "per_joint_own_phase", "torque_changed")},
                     indent=1, default=str))
