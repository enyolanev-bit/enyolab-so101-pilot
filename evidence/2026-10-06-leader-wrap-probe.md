# Sonde v2 — LEADER — franchissement 0/4095 (IDs 2, 3, 4) — lecture seule — RÉSULTAT : BLOCKED (incomplet, délai dépassé)

- **Date** : 2026-10-06, de 20:57:36 à 21:12:45 CEST
- **GO** : HQ, validation en lecture seule du franchissement, leader seul ; follower non alimenté (HUMAN_CONFIRMED)
- **Script** : `2026-10-06-leader_wrap_probe.py`, sha256 `0eed5eb16cf085df5dbbba21582c32b1f8c8183ca9fdf6b380b96ab6b10645e0`
  - revue de sécurité : aucun P0/P1 ; les 3 P2 et les P3 utiles ont été corrigés avant exécution ;
  - essais à blanc OK : refus d'un mauvais port, refus d'écraser, port inexistant, test unitaire du franchissement et des trous de lecture.
- **Port** : `/dev/cu.usbmodem5B7B0154401`, numéro de série `5B7B015440` vérifié par le script et par `ioreg`. Adaptateur follower non ouvert.
- **Logs** :
  - `2026-10-06T205736-leader-wrap-probe.json`, sha256 `e836ab593c51f7ab0428655a1100d1cd97d15e3b1912de3f767e65b031f29f38` ;
  - `2026-10-06T205736-leader-wrap-probe.samples.jsonl`, sha256 `69d7781ba628cc8d0c77d8398b962b1c3e923f9fdd9b30f6078e177692bb2cce`.

## Sécurité

| Élément | Valeur |
|---|---|
| Instructions émises | PING × 7, READ × 7545 ; aucune autre |
| Appels d'écriture | **0** (`blocked_calls` vide) |
| Commandes de couple | **0** ; `Torque_Enable` = 0 sur les 6 servos au début et à la fin |
| Erreurs de communication | 0 |
| Port fermé | oui, `port_handler.closePort()` direct ; `lsof` : port libre |

## Découverte et registres EEPROM relus (lecture seule)

`broadcast_ping` et `ping` : IDs 1 à 6, tous en modèle 777.

| ID | Moteur | Homing_Offset | Min | Max | Phase | = `pilot001_leader.json` |
|---|---|---|---|---|---|---|
| 1 | shoulder_pan | −2000 | 781 | 3512 | 76 (0x4C) | oui |
| 2 | shoulder_lift | 1063 | 1 | 4095 | **12 (0x0C)** | oui |
| 3 | elbow_flex | −1431 | 0 | 4095 | 76 | oui |
| 4 | wrist_flex | −349 | 0 | 4095 | 76 | oui |
| 5 | wrist_roll | 1928 | 0 | 4095 | 76 | oui |
| 6 | gripper | −1828 | 2010 | 3251 | 76 | oui |

- **La calibration écrite dans les servos est identique au fichier JSON**, pour les 6 servos (PROVEN).
- Bit 4 de `Phase` à 0 sur les 6 servos : lecture repliée dans [0, 4095], comme prévu.
- Observation non interprétée : le `Phase` de l'ID 2 diffère des autres par le **bit 6 (0x40)**. Sa signification n'est pas vérifiée.

## Échantillonnage

- La phase **ID2** n'a été activée qu'à **t = 841,9 s**, soit environ 58 s avant la limite de 900 s.
- **ID 2** (`shoulder_lift`) : 2499 échantillons (≈ 43 Hz). Position **constante à 2045**, Δ max = 0 : **l'articulation n'a pas bougé** pendant la fenêtre.
- **IDs 3 et 4** : non échantillonnés. Délai dépassé, la commande STOP n'a jamais été reçue.

## Résultat

- **RESULT = BLOCKED** : test incomplet, aucun parcours observé.
- ID2_WRAP / ID3_WRAP / ID4_WRAP = **NOT_TESTED**. Aucun franchissement n'a été observé, faute de mouvement : ce n'est ni une preuve d'absence, ni une preuve de présence.
- Seule indication mesurée : `shoulder_lift` **au repos** se trouve à 2045, soit ≈ le point de centrage (2047).

## Suite

Relancer la même sonde, sous un **nouveau préfixe de sortie** (la sonde refuse d'écraser), **une fois l'opérateur en place**, en enchaînant ID2 → ID3 → ID4 → STOP dans les 15 minutes.

## Addendum 21:19 CEST — phases opérateur non enregistrées

- L'opérateur rapporte avoir parcouru ID2, ID3 et ID4, puis envoyé STOP.
- Constat : le fichier de contrôle a été modifié en dernier à **21:17:54** (contenu `STOP`), alors que la sonde s'était **arrêtée à 21:12:45** (délai de 900 s dépassé). Aucun processus de sonde ne tournait ensuite (`pgrep`), et le port leader était libre (`lsof`).
- Ces parcours ont donc eu lieu **sans aucun enregistrement**. Ils ne constituent pas une preuve et ne changent pas le résultat.
- Dernier échantillon enregistré (t = 899,996 s, phase ID2) : ID2 = 2045, ID3 = 2040, ID4 = 2081, tous au repos, ≈ point de centrage.
- Fichiers d'origine **inchangés** :
  - `.json`, sha256 `e836ab593c51f7ab0428655a1100d1cd97d15e3b1912de3f767e65b031f29f38` ;
  - `.samples.jsonl`, sha256 `69d7781ba628cc8d0c77d8398b962b1c3e923f9fdd9b30f6078e177692bb2cce`.
- **Résultat inchangé : BLOCKED, IDs 2, 3 et 4 NOT_TESTED.** Relance nécessaire, sous un nouveau préfixe, lancée au moment où l'opérateur est prêt.
