# Premier test bus servo — LEADER — lecture seule — RÉSULTAT : BLOCKED (ID 5 absent)

- **Date** : 2026-10-05, 23:22:01 CEST
- **Hôte** : Mac ENYOLAB (bring-up), `.venv` du dépôt, LeRobot 0.6.1, `feetech-servo-sdk` 1.0.0
- **GO** : autorisation humaine explicite pour ce test, leader seul, lecture seule (ENYO-14)
- **État physique déclaré par l'opérateur (HUMAN_OBSERVED)** : leader mécaniquement complet ; bloc leader étiqueté `OUTPUT: 5V 4A` ; follower **non alimenté**. L'agent ne peut vérifier ni l'alimentation ni l'absence de mouvement.

## Pré-vérification (sans ouverture de port)

- `scripts/find_ports.sh` à 23:21:03 : `usbmodem5B7B0152071` et `usbmodem5B7B0154401` présents.
- `ioreg` : deux `USB Single Serial`, numéros de série USB `5B7B015207` et `5B7B015440`. Le nom de port `usbmodem5B7B0154401` dérive du numéro de série matériel `5B7B015440`, c'est-à-dire l'adaptateur identifié comme **leader** par débranchement contrôlé (`2026-10-05-serial-port-identification.md`).
- Seul `/dev/cu.usbmodem5B7B0154401` a été ouvert. L'adaptateur follower est resté branché en USB, **jamais ouvert**.

## Méthode

Script : `2026-10-05-leader_bus_probe.py` (sha256 `89d67a7f0cc76f87930b3ae6f160d96ca70f5af029fe4cba787738edbc57143c`). Il applique le chemin audité dans ENYO-14 :

- `FeetechMotorsBus` instancié directement : **ni** `SO101Leader`, **ni** classe robot ou téléopérateur.
- `connect(handshake=False)` : ouverture du port à 1 000 000 bauds, **0 paquet émis**.
- `broadcast_ping()`, puis `ping(1..6)`.
- Lectures prévues `read(..., normalize=False)`, **non atteintes** à cause de l'arrêt en découverte.
- Fermeture : `bus.port_handler.closePort()` direct. `disconnect()` n'a **pas** été appelé.

**Garde d'écriture active pendant tout le test** :
- toutes les méthodes d'écriture de LeRobot et du SDK sont remplacées par une fonction qui lève une exception et les compte (`write`, `sync_write`, `enable_torque`, `disable_torque`, `write_calibration`, `configure_motors`, `setup_motor`, `disconnect`, `write*TxRx/TxOnly`, `regWrite*`, `syncWriteTxOnly`, `action`, etc.) ;
- chaque paquet émis passe par un journal qui refuse toute instruction autre que `PING` (1) ou `READ` (2).

## Résultat

| Élément | Valeur |
|---|---|
| Port | `/dev/cu.usbmodem5B7B0154401` |
| Baudrate (côté Mac) | 1 000 000 |
| `broadcast_ping` | `{1: 777, 2: 777, 3: 777, 4: 777, 6: 777}` |
| `ping(i)` | 1 → 777, 2 → 777, 3 → 777, 4 → 777, **5 → aucune réponse**, 6 → 777 |
| IDs répondants | **[1, 2, 3, 4, 6]** — 5 sur 6 |
| Numéro de modèle | **777** (STS3215) pour les 5 répondants |
| ID manquant | **5** (`wrist_roll` dans le schéma LeRobot) |
| Lectures d'état | **non effectuées** — arrêt en découverte, conformément à la consigne |
| Paquets émis | 17, instructions `{1: PING, 2: READ}` uniquement |
| Appels d'écriture | **0** (`blocked_calls` vide) |
| Commandes de couple | **0** |
| Port fermé | **oui**, via `port_handler.closePort()` |
| Mouvement | **non observable par l'agent** — à confirmer par l'opérateur |

Log brut : `2026-10-05T232201-leader-bus-probe.json` (sha256 `fc042a50c69c9151afd833d7bec0c7494439c977bc17faa7aa0a65aeed0d01b6`).

**RESULT = BLOCKED** : 5 servos répondent au lieu de 6, l'ID 5 est absent.

## Lecture — hypothèses, aucune n'est tranchée

L'ID 5 ne répond **ni** au ping général **ni** au ping direct, et aucun ID inattendu n'apparaît. Causes compatibles, **non vérifiées** :

1. câble 3 fils du servo 5 débranché ou mal clipsé (la session 015 a déjà vu un câble traversant un joint sauter) ;
2. servo 5 non alimenté ou défectueux ;
3. servo 5 portant un autre ID, déjà pris : deux servos sur un même ID peuvent se masquer mutuellement sans erreur franche ;
4. servo 5 jamais configuré (ID usine 1 en doublon avec le servo 1) : même effet que le point 3.

Aucune réparation automatique n'a été tentée. Toute correction d'ID (`lerobot-setup-motors`, écriture EEPROM) exige une **décision distincte**.
