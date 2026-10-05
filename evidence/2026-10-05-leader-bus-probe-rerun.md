# Test bus servo LEADER — relance après correction câble ID 5 — lecture seule — RÉSULTAT : PASS

- **Date** : 2026-10-05, 23:42:47 CEST
- **Contexte (HUMAN_OBSERVED)** : l'opérateur a trouvé la cause de l'échec précédent. Le servo `wrist_roll` (ID 5 attendu) n'était pas câblé ; il vient d'être branché. Leader alimenté par un bloc `5V 4A` ; follower non alimenté.
- **Preuve précédente conservée, non modifiée** :
  - `2026-10-05-leader-bus-probe.md`, sha256 `54659387d6644770132db3bbb12f77cd010129dac5233e06acf49a707ea86434` ;
  - `2026-10-05T232201-leader-bus-probe.json`, sha256 `fc042a50c69c9151afd833d7bec0c7494439c977bc17faa7aa0a65aeed0d01b6` (revérifié avant relance).

## Méthode — identique, modèle de sécurité inchangé

- Script exécuté tel quel : `2026-10-05-leader_bus_probe.py`, sha256 `89d67a7f0cc76f87930b3ae6f160d96ca70f5af029fe4cba787738edbc57143c`, vérifié avant exécution.
- Pré-vérification à 23:42:39 : `find_ports.sh` montre `usbmodem5B7B0152071` et `usbmodem5B7B0154401`. `ioreg` donne les numéros de série `5B7B015207` / `5B7B015440`. Le port leader dérive toujours de l'adaptateur `5B7B015440`.
- Port ouvert : `/dev/cu.usbmodem5B7B0154401` **seulement**. L'adaptateur follower n'a pas été ouvert.
- Chemin :
  - `FeetechMotorsBus` direct (aucune classe `SO101Leader`, robot ou téléopérateur) ;
  - `connect(handshake=False)` à 1 000 000 bauds ;
  - `broadcast_ping`, puis `ping(1..6)` ;
  - `read(..., normalize=False)` sur 4 registres, puis 2e passe `Present_Position` / `Torque_Enable` après 0,5 s ;
  - `port_handler.closePort()` direct.
- Garde d'écriture et garde d'instruction de paquet **actives**, identiques à l'essai précédent.

## Résultats

| Élément | Valeur |
|---|---|
| `broadcast_ping` | `{1..6: 777}` |
| `ping(i)` | 777 pour i = 1..6 |
| IDs répondants | **[1, 2, 3, 4, 5, 6]** |
| Paquets émis | 55, instructions `{1: PING, 2: READ}` uniquement |
| Appels d'écriture | **0** (`blocked_calls` vide) |
| Commandes de couple | **0** |
| Port fermé | **oui** — `port_handler.closePort()`, `disconnect()` non appelé |
| Mouvement | **non observable par l'agent** ; confirmation de l'opérateur : **UNKNOWN** (non transmise). Aucune commande de mouvement ni de couple émise ; Δ position = 0 |

Valeurs brutes, `normalize=False`, sans calibration :

| ID | Nom LeRobot | Present_Position | Torque_Enable | Present_Voltage | Present_Temperature | Position, 2e lecture | Torque, 2e lecture | Δ position |
|---|---|---|---|---|---|---|---|---|
| 1 | shoulder_pan | 213 | 0 | 48 | 28 | 213 | 0 | 0 |
| 2 | shoulder_lift | 3112 | 0 | 49 | 28 | 3112 | 0 | 0 |
| 3 | elbow_flex | 712 | 0 | 49 | 28 | 712 | 0 | 0 |
| 4 | wrist_flex | 3724 | 0 | 49 | 30 | 3724 | 0 | 0 |
| 5 | wrist_roll | **−261** | 0 | 49 | 29 | −261 | 0 | 0 |
| 6 | gripper | 331 | 0 | 49 | 29 | 331 | 0 | 0 |

- **Couple** : `Torque_Enable = 0` sur les 6 servos, aux deux lectures. Aucun changement d'état.
- **Stabilité** : Δ position = 0 sur les 6 servos (0,5 s d'écart). Rien ne suggère de mouvement côté données ; l'observation visuelle revient à l'opérateur.
- **Tension** : 48-49 en valeur brute. Si l'unité est 0,1 V, ce qui **n'est pas vérifié**, cela fait 4,8-4,9 V, cohérent avec un bloc 5 V.
- **Température** : 28-30 en valeur brute (unité °C présumée, non vérifiée).

Log brut : `2026-10-05T234247-leader-bus-probe.json` (sha256 `7405f9ab344984a6df47aedf2a4a69397a81080345014d58d400ea1d1d4b3013`).

## Observation — ID 5, position décodée négative (pas un défaut en soi)

`Present_Position` de l'**ID 5 (`wrist_roll`) = −261** en valeur **décodée**. Ce n'est pas une anomalie en soi :
- dans LeRobot 0.6.1, `Present_Position` des STS3215 est encodé en **signe-magnitude**, bit de signe 15 (`motors/feetech/tables.py` l.213, `STS_SMS_SERIES_ENCODINGS_TABLE`) ;
- `bus.read(..., normalize=False)` applique **quand même** `_decode_sign()` (`motors/motors_bus.py` l.1023, avant le test `normalize`) ;
- une valeur négative est donc un résultat normal du décodage d'un mot brut dont le bit 15 vaut 1. Mot brut correspondant **calculé**, non lu : 32 768 + 261 = 33 029.

**Correction (décision HQ, 2026-10-05)** : le critère « `Present_Position` ∈ [0, 4095] » proposé dans l'audit ENYO-14 était **erroné** pour une valeur décodée. On ne conclut pas qu'ID 5 est défectueux ou mal configuré sur ce seul signe. La signification physique de cette position, par rapport à la course du poignet, sera traitée lors de la calibration, sur GO distinct. Hypothèse **ASSUMED**, registre non lu : un `Homing_Offset` non nul en EEPROM sur l'ID 5.

## Résultat

**RESULT = PASS** : 6 servos, IDs 1 à 6, modèle 777, lectures d'état réussies et stables, aucune écriture, aucune commande de couple, port fermé.
## Suite à donner (revue gstack)

- **P2 — avant toute nouvelle exécution** : le script `2026-10-05-leader_bus_probe.py` écrase son fichier de sortie s'il existe déjà. Il reste **inchangé ici**, puisque son SHA est cité. Une **v2** devra :
  - refuser d'écrire sur un fichier existant ;
  - écrire le journal même en cas d'interruption ;
  - vérifier que le port porte bien le numéro de série du leader (`5B7B015440`).

Aucune calibration effectuée. STOP.
