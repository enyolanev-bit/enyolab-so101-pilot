"""Sonde bus servo LEADER — lecture seule (ENYO-14).

Chemin audite (LeRobot 0.6.1) : FeetechMotorsBus direct, connect(handshake=False),
broadcast_ping, ping, read(normalize=False), port_handler.closePort().
Garde : toute methode d'ecriture leve une exception ; chaque paquet emis est
journalise avec son code d'instruction ; arret si code hors {PING=1, READ=2}.
"""
import json, sys, time, hashlib, pathlib, datetime
import scservo_sdk as scs
from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus

PORT = sys.argv[1]
OUT = pathlib.Path(sys.argv[2])
NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
ALLOWED_INST = {scs.INST_PING: "PING", scs.INST_READ: "READ"}
REGS = ["Present_Position", "Torque_Enable", "Present_Voltage", "Present_Temperature"]

log = {"started": datetime.datetime.now().astimezone().isoformat(), "port": PORT,
       "method": "FeetechMotorsBus direct; connect(handshake=False); broadcast_ping; ping; read(normalize=False); port_handler.closePort()",
       "tx_packets": [], "write_calls": 0, "blocked_calls": [], "steps": [], "result": None}

class WriteGuard(RuntimeError):
    pass

def guard(name):
    def _blocked(*a, **k):
        log["write_calls"] += 1
        log["blocked_calls"].append(name)
        raise WriteGuard(f"write path reached: {name}")
    return _blocked

bus = FeetechMotorsBus(port=PORT, calibration=None,
                       motors={n: Motor(i, "sts3215", MotorNormMode.RANGE_M100_100) for i, n in enumerate(NAMES, 1)})

# --- garde ecriture : niveau LeRobot ---
for m in ("write", "sync_write", "_write", "_sync_write", "enable_torque", "disable_torque",
          "_disable_torque", "write_calibration", "reset_calibration", "configure_motors",
          "setup_motor", "set_half_turn_homings", "disconnect"):
    setattr(bus, m, guard(f"bus.{m}"))
# --- garde ecriture : niveau SDK ---
ph = bus.packet_handler
for m in ("writeTxOnly", "writeTxRx", "write1ByteTxOnly", "write1ByteTxRx", "write2ByteTxOnly",
          "write2ByteTxRx", "write4ByteTxOnly", "write4ByteTxRx", "regWriteTxOnly", "regWriteTxRx",
          "syncWriteTxOnly", "action"):
    setattr(ph, m, guard(f"packet_handler.{m}"))
# --- journal de chaque paquet emis + arret si instruction non autorisee ---
_orig_tx = ph.txPacket
def _tx(port, txpacket):
    inst = txpacket[scs.PKT_INSTRUCTION]; pid = txpacket[scs.PKT_ID]
    log["tx_packets"].append({"id": pid, "inst": inst, "inst_name": ALLOWED_INST.get(inst, "FORBIDDEN")})
    if inst not in ALLOWED_INST:
        log["write_calls"] += 1
        raise WriteGuard(f"forbidden instruction {inst} to id {pid}")
    return _orig_tx(port, txpacket)
ph.txPacket = _tx

def step(name, **kw):
    log["steps"].append({"t": round(time.monotonic(), 3), "step": name, **kw})

abort = None
try:
    bus.connect(handshake=False)
    step("connect(handshake=False)", baudrate=bus.port_handler.getBaudRate(), tx_after_connect=len(log["tx_packets"]))

    bp = bus.broadcast_ping()
    step("broadcast_ping", result=bp)
    per_id = {i: bus.ping(i) for i in range(1, 7)}
    step("ping 1..6", result=per_id)

    ids_bp = sorted(bp) if bp else []
    models = {i: per_id[i] for i in range(1, 7)}
    log["responding_ids_broadcast"] = ids_bp
    log["model_numbers_ping"] = models
    if ids_bp != [1, 2, 3, 4, 5, 6] or any(models[i] is None for i in models):
        abort = "DISCOVERY: ids/models != expected"
    elif set(models.values()) != {777} or set(bp.values()) != {777}:
        abort = "DISCOVERY: model number != 777 (sts3215)"

    if abort is None:
        reads = {}
        for i, n in enumerate(NAMES, 1):
            reads[i] = {r: bus.read(r, n, normalize=False) for r in REGS}
        step("reads pass 1", result=reads)
        time.sleep(0.5)
        reads2 = {}
        for i, n in enumerate(NAMES, 1):
            reads2[i] = {r: bus.read(r, n, normalize=False) for r in ("Present_Position", "Torque_Enable")}
        step("reads pass 2 (stabilite)", result=reads2)
        log["servo_reads"] = reads
        log["servo_reads_pass2"] = reads2
        log["position_delta"] = {i: reads2[i]["Present_Position"] - reads[i]["Present_Position"] for i in reads}
        log["torque_changed"] = any(reads2[i]["Torque_Enable"] != reads[i]["Torque_Enable"] for i in reads)
        if log["torque_changed"]:
            abort = "TORQUE STATE CHANGED"
except WriteGuard as e:
    abort = f"WRITE GUARD: {e}"
except Exception as e:
    abort = f"{type(e).__name__}: {e}"
finally:
    try:
        if bus.port_handler.is_open:
            bus.port_handler.closePort()
        log["port_closed"] = not bus.port_handler.is_open
        log["close_path"] = "bus.port_handler.closePort() (direct; disconnect() NOT called)"
    except Exception as e:
        log["port_closed"] = False
        log["close_error"] = repr(e)

inst_set = sorted({p["inst"] for p in log["tx_packets"]})
log["instructions_emitted"] = {str(k): ALLOWED_INST.get(k, "FORBIDDEN") for k in inst_set}
log["tx_packet_count"] = len(log["tx_packets"])
log["abort"] = abort
log["result"] = "PASS" if abort is None and log["write_calls"] == 0 and log.get("port_closed") else "BLOCKED"
log["finished"] = datetime.datetime.now().astimezone().isoformat()
OUT.write_text(json.dumps(log, indent=1, default=str))
print(json.dumps({k: log[k] for k in ("result", "abort", "write_calls", "port_closed", "instructions_emitted",
                                       "tx_packet_count")}, indent=1))
