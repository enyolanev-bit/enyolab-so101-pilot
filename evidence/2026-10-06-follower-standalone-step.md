# Premier mouvement autonome du follower (+1° `shoulder_pan`) — 2026-10-06 23:04:41 CEST — RÉSULTAT : BLOCKED (erreur de communication, avant activation du couple)

- **GO** : HQ, un seul mouvement autonome de +1° sur `shoulder_pan`, sans leader.
- **Script** : `2026-10-06-follower_standalone_step.py`, sha256 `fa8b7618d8801a36e1f1268eb3ca35622d3fa1f3cb8a87fc24f4029f1ab10ba9`.
  - Dérivé des briques auditées du lanceur : garde-fous statiques, liste blanche par adresse, couple à 1 seulement au point autorisé, recalage vérifié avant `enable_torque`, arrêt sûr.
  - Essais à blanc OK : refus sans `--go` ; contrôles statiques, puis échec avant toute écriture sur port factice.
- **Calibration** : `follower_nevil.json`, sha256 `f48d50d5…` (vérifié).
- **Journal** : `2026-10-06T230441-follower-step.events.json`, sha256 `196661544b9edf369e3bf2c2f422764643b504d34ae78db618af52095ca3fa7e`. `…steps.jsonl` vide : maintien de 4 s non atteint.

## Déroulé

| Étape | Résultat |
|---|---|
| Contrôles statiques (version, empreintes, SHA, numéro de série) | OK |
| Handshake, IDs 1..6 (777), couple 0, registres == fichier | OK |
| Pose initiale (brut) | 2085 / 2024 / 2047 / 101 / 951 / 2140 |
| `Goal_Position` avant | **déjà = position présente** (recalage de 22:56 conservé en RAM) |
| Plages (marge 20, `wrist_flex` 5) | OK |
| `configure()` | écritures auditées (40=0, 55=0, 7, 85, 41, 33, P/D/I, pince 16/28/36) |
| Recalage : écriture `Goal_Position` ×6 | **acquittée** (2085 / 2024 / 2047 / 101 / 951 / 2140) |
| Relecture groupée de `Goal_Position` | **ÉCHEC** : `ConnectionError … Failed to sync read 'Goal_Position' on ids=[1..6] after 1 tries. [TxRxResult] Incorrect status packet!` |
| Activation du couple, maintien 4 s, pas de +1°, mesure | **non atteints** |

## Sécurité

- **Couple jamais activé.** L'exception est levée dans le remplacement de `enable_torque`, avant l'appel à l'activation réelle.
- Écritures : uniquement celles de la liste blanche. Arrêt : 40=0 ×6, couple **relu à 0** ×6, port fermé.
- Aucun mouvement commandé.

## Lecture

- Erreur de communication **isolée** sur une lecture groupée (`INST_SYNC_READ`). Les lectures groupées précédentes de la même session (couple, registres, positions) et les 6 écritures avec accusé ont réussi.
- Cause **UNKNOWN** : parasite ponctuel du bus, câblage, alimentation, ou robustesse de la lecture groupée.
- La règle d'abandon a fonctionné : aucune nouvelle tentative, aucun couple.

## Options (décision HQ)

1. Mesurer la fiabilité du bus follower en **lecture seule** : par exemple 1000 lectures groupées de `Present_Position` et `Goal_Position`, avec le taux d'erreur. Contrôler le câblage et l'alimentation 12 V.
2. Autoriser **une relance de lecture** (`num_retry=2`, comme le défaut LeRobot `num_read_retries=2`) dans les seules **relectures de vérification**, l'abandon restant la règle en cas d'échec persistant. Modification de code à relire.
3. Relancer le même script tel quel : risque de nouvel abandon si l'erreur se répète.
