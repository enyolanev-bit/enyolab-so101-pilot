"""Sonde de concordance des poses leader / follower — LECTURE SEULE (ENYO-14).

Les deux bras sont places a la main dans une pose aussi proche que possible. Pour chaque bras,
un a la fois : FeetechMotorsBus direct, connect(handshake=False), ping 1..6, puis 10 lectures de
Present_Position par read(normalize=True) avec la calibration chargee depuis le FICHIER
(SHA-256 verifie). La normalisation est la meme que celle de LeRobot 0.6.1 : _normalize,
DEGREES pour les articulations 1-5, RANGE_0_100 pour la pince, use_degrees=True. Les valeurs
brutes sont aussi relues.
Gardes : toute ecriture leve une exception ; seules les instructions PING et READ sont emises.
Fermeture par port_handler.closePort() direct. Aucun couple, aucune ecriture.

Usage : python pose_match_probe.py <out_json>
"""
import json, sys, time, signal, hashlib, pathlib, datetime
import scservo_sdk as scs
from lerobot.motors import Motor, MotorNormMode, MotorCalibration
from lerobot.motors.feetech import FeetechMotorsBus

OUT = pathlib.Path(sys.argv[1])
if OUT.exists():
    sys.exit(f"ABORT: refusing to overwrite {OUT}")
CAL = pathlib.Path.home() / ".cache/huggingface/lerobot/calibration"
ARMS = {
    "follower": {"port": "/dev/cu.usbmodem5B7B0152071", "serial": "5B7B015207",
                 "cal": CAL / "robots/so_follower/follower_nevil.json",
                 "sha": "f48d50d5ba8c220f13575f13c1d6562d9431391fb1e726541abdaf2c4e714a9d"},
    "leader": {"port": "/dev/cu.usbmodem5B7B0154401", "serial": "5B7B015440",
               "cal": CAL / "teleoperators/so_leader/pilot001_leader.json",
               "sha": "974f819f98567cb7c88fb746d389a9424f88a6fc531fb0587343e5285e4c0dae"},
}
NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
ALLOWED_INST = {scs.INST_PING: "PING", scs.INST_READ: "READ"}
N_SAMPLES = 10
TOL = 5.0
signal.signal(signal.SIGTERM, lambda s, f: (_ for _ in ()).throw(KeyboardInterrupt(f"signal {s}")))

class WriteGuard(RuntimeError):
    pass

log = {"started": datetime.datetime.now().astimezone().isoformat(), "arms": {}, "write_calls": 0, "abort": None}

def guard(name):
    def _b(*a, **k):
        log["write_calls"] += 1
        raise WriteGuard(name)
    return _b

def probe(arm, spec):
    rec = {"port": spec["port"], "tx_counts": {}}
    if spec["serial"] not in spec["port"]:
        raise RuntimeError(f"{arm}: port/serial mismatch")
    raw = spec["cal"].read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    rec["calibration_sha256"] = sha
    if sha != spec["sha"]:
        raise RuntimeError(f"{arm}: calibration sha {sha[:12]} != {spec['sha'][:12]}")
    calib = {m: MotorCalibration(**v) for m, v in json.loads(raw).items()}
    motors = {n: Motor(i, "sts3215", MotorNormMode.RANGE_0_100 if n == "gripper" else MotorNormMode.DEGREES)
              for i, n in enumerate(NAMES, 1)}
    bus = FeetechMotorsBus(port=spec["port"], motors=motors, calibration=calib)
    for m in ("write", "sync_write", "_write", "_sync_write", "enable_torque", "disable_torque", "_disable_torque",
              "write_calibration", "reset_calibration", "configure_motors", "setup_motor", "set_half_turn_homings",
              "disconnect"):
        setattr(bus, m, guard(f"bus.{m}"))
    ph = bus.packet_handler
    for m in ("writeTxOnly", "writeTxRx", "write1ByteTxOnly", "write1ByteTxRx", "write2ByteTxOnly", "write2ByteTxRx",
              "write4ByteTxOnly", "write4ByteTxRx", "regWriteTxOnly", "regWriteTxRx", "syncWriteTxOnly", "action"):
        setattr(ph, m, guard(f"ph.{m}"))
    orig_tx = ph.txPacket
    def tx(port, pkt):
        inst = pkt[scs.PKT_INSTRUCTION]
        rec["tx_counts"][ALLOWED_INST.get(inst, f"FORBIDDEN_{inst}")] = rec["tx_counts"].get(ALLOWED_INST.get(inst, f"FORBIDDEN_{inst}"), 0) + 1
        if inst not in ALLOWED_INST:
            log["write_calls"] += 1
            raise WriteGuard(f"instruction {inst}")
        return orig_tx(port, pkt)
    ph.txPacket = tx
    try:
        bus.connect(handshake=False)
        ping = {i: bus.ping(i) for i in range(1, 7)}
        rec["ping"] = ping
        if any(v != 777 for v in ping.values()):
            raise RuntimeError(f"{arm}: ids/models {ping}")
        rec["torque"] = {n: bus.read("Torque_Enable", n, normalize=False) for n in NAMES}
        rec["registers"] = {n: {r: bus.read(r, n, normalize=False) for r in ("Homing_Offset", "Min_Position_Limit", "Max_Position_Limit")}
                            for n in NAMES}
        rec["registers_match_file"] = all(
            (rec["registers"][n]["Homing_Offset"], rec["registers"][n]["Min_Position_Limit"], rec["registers"][n]["Max_Position_Limit"])
            == (calib[n].homing_offset, calib[n].range_min, calib[n].range_max) for n in NAMES)
        samples_norm, samples_raw = {n: [] for n in NAMES}, {n: [] for n in NAMES}
        for _ in range(N_SAMPLES):
            for n in NAMES:
                samples_raw[n].append(bus.read("Present_Position", n, normalize=False))
                samples_norm[n].append(bus.read("Present_Position", n, normalize=True))
            time.sleep(0.05)
        rec["raw_mean"] = {n: sum(v) / len(v) for n, v in samples_raw.items()}
        rec["raw_spread"] = {n: max(v) - min(v) for n, v in samples_raw.items()}
        rec["norm_mean"] = {n: sum(v) / len(v) for n, v in samples_norm.items()}
        rec["mid"] = {n: (calib[n].range_min + calib[n].range_max) / 2 for n in NAMES}
        rec["torque_end"] = {n: bus.read("Torque_Enable", n, normalize=False) for n in NAMES}
    finally:
        ser = getattr(bus.port_handler, "ser", None)
        if bus.port_handler.is_open or (ser is not None and ser.is_open):
            bus.port_handler.closePort()
        rec["port_closed"] = not bus.port_handler.is_open
    return rec

try:
    for arm, spec in ARMS.items():            # un bras a la fois
        log["arms"][arm] = probe(arm, spec)
except Exception as e:
    log["abort"] = f"{type(e).__name__}: {e}"
finally:
    if not log["abort"] and len(log["arms"]) == 2:
        f, l = log["arms"]["follower"], log["arms"]["leader"]
        log["comparison"] = {n: {"leader": round(l["norm_mean"][n], 2), "follower": round(f["norm_mean"][n], 2),
                                 "abs_diff": round(abs(l["norm_mean"][n] - f["norm_mean"][n]), 2),
                                 "exceeds_5": abs(l["norm_mean"][n] - f["norm_mean"][n]) > TOL,
                                 "leader_raw": round(l["raw_mean"][n], 1), "leader_mid": l["mid"][n],
                                 "follower_raw": round(f["raw_mean"][n], 1), "follower_mid": f["mid"][n]}
                             for n in NAMES}
    log["finished"] = datetime.datetime.now().astimezone().isoformat()
    with open(OUT, "x") as fh:
        json.dump(log, fh, indent=1, default=str)
    print(json.dumps({"abort": log["abort"], "write_calls": log["write_calls"],
                      "comparison": log.get("comparison"),
                      "torque": {a: (r.get("torque"), r.get("torque_end")) for a, r in log["arms"].items()},
                      "registers_match_file": {a: r.get("registers_match_file") for a, r in log["arms"].items()},
                      "spread": {a: r.get("raw_spread") for a, r in log["arms"].items()},
                      "port_closed": {a: r.get("port_closed") for a, r in log["arms"].items()},
                      "tx": {a: r.get("tx_counts") for a, r in log["arms"].items()}}, indent=1, default=str))
