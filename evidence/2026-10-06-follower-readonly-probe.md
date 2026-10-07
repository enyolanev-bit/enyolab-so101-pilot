# Revalidation FOLLOWER — lecture seule — 2026-10-06 22:10 CEST — RÉSULTAT : PASS

- **GO** : HQ, revalidation du follower en lecture seule. Aucune téléopération.
- **État déclaré (HUMAN_CONFIRMED)** : follower déjà alimenté, bloc **12 V**, 6 câbles servo branchés. Marquage des servos : **non relevé**.
- **Pré-vérification** (22:09:52, sans ouverture de port) : `find_ports.sh` montre `usbmodem5B7B0152071` et `usbmodem5B7B0154401` ; `ioreg` donne les numéros de série `5B7B015207` et `5B7B015440`. Le port follower dérive de `5B7B015207`, l'adaptateur resté branché lors du débranchement contrôlé du 2026-10-05. Port libre.
- **Script** : `2026-10-06-follower_readonly_probe.py`, sha256 `19e2a82c1e87265a5c9f8d99dcbfc6c2f84e340bdc0206150b4b9dc40a1a4fc7`
  - chemin audité : `FeetechMotorsBus` direct, `connect(handshake=False)`, ping, `read(normalize=False)`, `closePort()` direct ;
  - **ni** `SOFollower`, **ni** `connect()` normal (qui réactiverait le couple) ;
  - garde d'écriture et garde d'instruction ; port vérifié par numéro de série ; refus d'écraser ;
  - essais à blanc OK : mauvais port, port inexistant, refus d'écraser.
- **Calibration** : `follower_nevil.json` lu comme **fichier** (json.load), sha256 `f48d50d5ba8c220f13575f13c1d6562d9431391fb1e726541abdaf2c4e714a9d` ; **jamais écrit aux moteurs**.
- **Log** : `2026-10-06T221031-follower-readonly-probe.json`, sha256 `8022013c9e4b59ca2fa7ab8116815535fe5fa2e43f84e61ac38a4e76c068a9d3`

## Sécurité

| Élément | Valeur |
|---|---|
| Instructions | PING × 7, READ × 72 ; aucune autre |
| Appels d'écriture | **0** |
| Commandes de couple | **0** ; `Torque_Enable` = 0 sur les 6 servos, aux deux lectures |
| Port | fermé par `closePort()` direct ; `lsof` : libre ; port leader non ouvert |

## Lectures brutes (`normalize=False`)

| ID | Moteur | Model | Torque | Present_Position | Present_Voltage | Present_Temperature | Homing_Offset | Min | Max | Phase |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | shoulder_pan | 777 | 0 | 2087 | 118 | 34 | −1634 | 857 | 3266 | 12 |
| 2 | shoulder_lift | 777 | 0 | 2091 | 119 | 35 | 1693 | 0 | 4095 | 12 |
| 3 | elbow_flex | 777 | 0 | 2050 | 119 | 33 | −1340 | 0 | 4095 | 12 |
| 4 | wrist_flex | 777 | 0 | 1570 | 119 | 35 | −1147 | 91 | 2414 | 12 |
| 5 | wrist_roll | 777 | 0 | 953 | 118 | 35 | −1084 | 0 | 4095 | 12 |
| 6 | gripper | 777 | 0 | 2140 | 118 | 36 | 900 | 2029 | 3540 | 12 |

- `broadcast_ping` et `ping` : IDs **1 à 6**, tous en modèle **777** (STS3215).
- Tension brute 118-119 : ≈ 11,8-11,9 V **si** l'unité est 0,1 V (non vérifié). Cohérent avec le bloc 12 V déclaré.
- Température brute 33-36 (°C présumés).

## Comparaison calibration fichier ↔ registres

| Moteur | Fichier [homing, min, max] | Servo [homing, min, max] | Concordance |
|---|---|---|---|
| shoulder_pan | [−1634, 857, 3266] | [−1634, 857, 3266] | oui |
| shoulder_lift | [1693, 0, 4095] | [1693, 0, 4095] | oui |
| elbow_flex | [−1340, 0, 4095] | [−1340, 0, 4095] | oui |
| wrist_flex | [−1147, 91, 2414] | [−1147, 91, 2414] | oui |
| wrist_roll | [−1084, 0, 4095] | [−1084, 0, 4095] | oui |
| gripper | [900, 2029, 3540] | [900, 2029, 3540] | oui |

**MISMATCHES = aucun.** Les IDs du fichier correspondent aussi (1..6).

## Lecture

- **PROVEN** : les registres de calibration du follower physique actuel sont identiques à `follower_nevil.json` (fichier du 2026-09-11).
- **ASSUMED (fort)** : c'est le **même bras** que celui de la session 015 (`lab-hardware`, 2026-07-26), décrit avec 6 × ST-3215-C047 en gamme 12 V. Un même jeu d'offsets et de limites sur 6 servos ne s'obtient pas par hasard. Combiné au 12 V mesuré, cela soutient la variante **C047 / 12 V**. Le **marquage visuel reste à relever** pour passer en PROVEN.
- **Calibration** : concordance fichier ↔ servo ne veut pas dire calibration valide. `shoulder_lift` et `elbow_flex` restent à 0..4095 (TO_REVALIDATE, même motif que le leader). `wrist_roll` 0..4095 est attendu. Ces limites EEPROM à 0..4095 signifient aussi **aucune butée logicielle côté servo** sur `shoulder_lift` et `elbow_flex`.
- `Phase` = 12 (bit 4 à 0) sur les 6 servos.

**RESULT = PASS** pour la revalidation en lecture seule. Aucune téléopération autorisée par ce résultat.
