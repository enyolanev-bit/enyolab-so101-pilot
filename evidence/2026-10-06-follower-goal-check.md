# Contrôle `Goal_Position` périmé — FOLLOWER — lecture seule — 2026-10-06 22:20 CEST — RÉSULTAT : BLOCKED

- **GO** : HQ, contrôle avant première téléopération, lecture seule.
- **Port** : `/dev/cu.usbmodem5B7B0152071`, numéro de série `5B7B015207` revérifié (`ioreg`) ; port libre avant et après ; aucun autre processus.
- **Script** : `2026-10-06-follower_goal_check.py`, sha256 `c13a57d502e60b5a71dc4b9d0a727b76ee9554754e1ced53b31f33b9a719f084`. Dérivé de la sonde follower relue ; mêmes gardes ; port vérifié par numéro de série ; refus d'écraser ; essais à blanc OK.
- **Log** : `2026-10-06T222041-follower-goal-check.json`, sha256 `077235f248f269f60af9ae273ad5329b911c16f1e000976d3c5e0b47a90b75ba`.

## Sécurité

| Élément | Valeur |
|---|---|
| Instructions | PING × 7, READ × 36 ; aucune autre |
| Appels d'écriture | **0** |
| `Torque_Enable` | 0 sur les 6 servos, aux deux lectures ; inchangé |
| Port | fermé par `closePort()` direct |

## Mesures (`normalize=False`, valeurs décodées)

| ID | Moteur | Goal_Position | Present_Position | Écart brut | Écart circulaire (4096) | ≤ 20 ? |
|---|---|---|---|---|---|---|
| 1 | shoulder_pan | **0** | 2085 | 2085 | 2011 | non |
| 2 | shoulder_lift | **0** | 2024 | 2024 | 2024 | non |
| 3 | elbow_flex | **0** | 2047 | 2047 | 2047 | non |
| 4 | wrist_flex | **0** | 103 | 103 | 103 | non |
| 5 | wrist_roll | **0** | 951 | 951 | 951 | non |
| 6 | gripper | **0** | 2140 | 2140 | 1956 | non |

## Lecture

- **`Goal_Position` = 0 sur les 6 servos** : la consigne en mémoire ne correspond pas aux positions présentes. Écart circulaire jusqu'à 2047 pas, soit ≈ 180°.
- Au moment du `enable_torque()` final de `SOFollower.connect()` (`so_follower.py` l.159-171, `motors_bus.py` l.677-691), chaque servo chercherait à rejoindre cette consigne **avant** la première borne `max_relative_target` de la boucle. Ce comportement n'a **pas été vérifié** sur le matériel.
- Sur `shoulder_lift` et `elbow_flex`, les limites EEPROM sont à 0..4095 : **aucune limite servo** ne bornerait le mouvement vers 0. Sur les autres, `Min_Position_Limit` pourrait borner la consigne, mais avec un mouvement **ample**. Pas de valeur exacte : comportement firmware non vérifié.
- Constat annexe : `wrist_flex` lit 103 ici contre 1570 à 22:10. L'articulation a bougé entre les deux sondes, couple à 0 (manipulation ou gravité ; cause non observée).
- **Risque** : une première téléopération lancée en l'état provoquerait très probablement un **mouvement brusque et ample du follower** dès la connexion.

**RESULT = BLOCKED**. Téléopération **non autorisée** en l'état.

## Pistes (non exécutées — décision HQ et GO distinct requis, car elles écrivent)

1. **Recaler la consigne avant le couple** : couple à 0, écrire `Goal_Position := Present_Position` sur les 6 servos (registre RAM, adr. 42), relire pour vérifier, puis lancer la téléopération **sans toucher au follower entre les deux**. Écriture minimale et vérifiable, mais faite **hors** LeRobot.
2. Faire de même dans un petit lanceur qui encapsule `SOFollower.connect()` : recalage juste avant `enable_torque()`. Plus robuste au délai, mais demande un code relu.
3. Vérifier d'abord, sur un **seul** servo à faible enjeu (pince), en GO dédié et avec la main sur la coupure 12 V, si l'activation du couple fait bien bouger le servo vers `Goal_Position`. Cela confirmerait le comportement du firmware.
