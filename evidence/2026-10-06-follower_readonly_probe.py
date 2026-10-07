"""Sonde FOLLOWER — revalidation LECTURE SEULE (ENYO-14).

Chemin audite (LeRobot 0.6.1) : FeetechMotorsBus direct ; connect(handshake=False) ;
broadcast_ping ; ping 1..6 ; read(normalize=False) ; port_handler.closePort().
Jamais SOFollower ni connect() normal (qui reactive le couple du follower).
Gardes : toute methode d'ecriture leve une exception ; chaque paquet est journalise et
refuse si l'instruction n'est pas PING (1) ou READ (2).
Le fichier de calibration est lu comme FICHIER uniquement (json.load), jamais ecrit aux moteurs.

Usage : python follower_readonly_probe.py <port> <out_json> <calibration_json>
"""
import json, sys, signal, hashlib, pathlib, datetime
import scservo_sdk as scs
from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus

PORT, OUT, CAL = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
EXPECTED_SERIAL = "5B7B015207"          # adaptateur follower (identification du 2026-10-05)
NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
REGS = ["Model_Number", "Torque_Enable", "Present_Position", "Present_Voltage", "Present_Temperature",
        "Homing_Offset", "Min_Position_Limit", "Max_Position_Limit", "Phase"]
ALLOWED_INST = {scs.INST_PING: "PING", scs.INST_READ: "READ"}

if EXPECTED_SERIAL not in PORT:
    sys.exit(f"ABORT: port {PORT} does not carry follower serial {EXPECTED_SERIAL}")
if OUT.exists():
    sys.exit(f"ABORT: refusing to overwrite {OUT}")

cal_bytes = CAL.read_bytes()
log = {"started": datetime.datetime.now().astimezone().isoformat(), "port": PORT,
       "method": "FeetechMotorsBus direct; connect(handshake=False); broadcast_ping; ping; "
                 "read(normalize=False); port_handler.closePort()",
       "calibration_file": str(CAL.name), "calibration_sha256": hashlib.sha256(cal_bytes).hexdigest(),
       "tx_counts": {}, "write_calls": 0, "blocked_calls": [], "abort": None}
calib = json.loads(cal_bytes)

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

try:
    bus.connect(handshake=False)
    bp = bus.broadcast_ping()
    per_id = {i: bus.ping(i) for i in range(1, 7)}
    log["broadcast_ping"] = bp
    log["ping"] = per_id
    if sorted(bp or {}) != [1, 2, 3, 4, 5, 6] or any(per_id[i] != 777 for i in per_id):
        raise RuntimeError("DISCOVERY: ids/models != expected [1..6] / 777")
    log["regs"] = {i: {r: bus.read(r, n, normalize=False) for r in REGS} for i, n in enumerate(NAMES, 1)}
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

    comparison, mismatches = {}, []
    regs = log.get("regs")
    if regs:
        for i, n in enumerate(NAMES, 1):
            c = calib.get(n, {})
            r = regs[i]
            row = {"file_id": c.get("id"), "file": [c.get("homing_offset"), c.get("range_min"), c.get("range_max")],
                   "motor": [r["Homing_Offset"], r["Min_Position_Limit"], r["Max_Position_Limit"]]}
            row["match"] = (c.get("id") == i and row["file"] == row["motor"])
            comparison[n] = row
            if not row["match"]:
                mismatches.append({"motor": n, "id": i, **row})
        log["torque_changed"] = {i: regs[i]["Torque_Enable"] for i in regs} != log.get("torque_end")
    log["calibration_comparison"] = comparison
    log["mismatches"] = mismatches
    ok = log["abort"] is None and log["write_calls"] == 0 and log.get("port_closed") and regs is not None \
        and log.get("torque_changed") is False
    log["result"] = "PASS" if ok else "BLOCKED"
    log["finished"] = datetime.datetime.now().astimezone().isoformat()
    with open(OUT, "x") as f:
        json.dump(log, f, indent=1, default=str)
    print(json.dumps({k: log.get(k) for k in ("result", "abort", "write_calls", "port_closed", "tx_counts",
                                               "torque_changed", "mismatches")}, indent=1, default=str))
