# Première téléopération (preuve de vie, `shoulder_pan` seulement) — 2026-10-06 22:46:47 CEST — RÉSULTAT : ABORTED avant activation du couple

- **GO** : HQ, pour ce test unique.
  - Calibration leader approuvée : `pilot001_leader.json`, sha256 `974f819f98567cb7c88fb746d389a9424f88a6fc531fb0587343e5285e4c0dae`.
  - Calibration follower : `follower_nevil.json`, sha256 `f48d50d5ba8c220f13575f13c1d6562d9431391fb1e726541abdaf2c4e714a9d`.
- **Porte physique (HUMAN_CONFIRMED)** : espace du follower dégagé, follower soutenu, coupure 12 V à portée, aucun câble tendu ou pincé.
- **Lanceur** : `2026-10-06-first_teleop_launcher.py`, sha256 `c5baac1c13d5881c4ebcd93844c8a0cb3b278ac7406ab5be6088c3cc781bca45`. Seul changement par rapport à la version relue (`32860405…`) : l'épinglage `LEADER_CAL_SHA256` approuvé par HQ.
- **Pré-vérification** (22:46:34) : SHA des deux fichiers de calibration conformes ; `ioreg` donne les numéros de série `5B7B015440` (leader) et `5B7B015207` (follower) ; ports libres ; aucun autre processus.
- **Journaux** :
  - `2026-10-06T224647-first-teleop.events.json`, sha256 `38aeda43fb2f12326b6ddf02886cd6240b8a3987a267715cd0c77f0eb75fcf64` ;
  - `2026-10-06T224647-first-teleop.steps.jsonl`, vide : aucune boucle.

## Déroulé

| Étape | Résultat |
|---|---|
| Contrôles statiques (LeRobot 0.6.1, 26 empreintes de code, SHA des calibrations, numéros de série) | OK |
| Follower : handshake, IDs 1..6, modèle 777 | OK |
| Follower : `Torque_Enable` initial | 0 sur les 6 |
| Follower : `is_calibrated` (registres == `follower_nevil.json`) | OK |
| Follower : registres journalisés | `Goal_Position` = **0** ×6 ; `Goal_Time` = 0 ×6 ; `Goal_Velocity` = **0** ×6 ; `Torque_Limit` = 1000 ×5, 500 (pince) |
| Follower : position dans [range_min+20, range_max−20] | **ÉCHEC** : `wrist_flex` = **103** < 91 + 20 = 111 |
| Recalage `Goal_Position`, activation du couple, leader, boucle | **non atteints** |

**Abandon** : `ABORT[follower_precheck]: follower wrist_flex present 103 outside [91+20, 2414-20]`.

## Sécurité

- **Couple du follower jamais activé.** Le point de recalage et d'activation n'a pas été atteint.
- Écritures : **6 × `Torque_Enable = 0`** (adr. 40), pendant l'arrêt sûr ; le couple était déjà à 0. Aucune autre écriture. Garde d'écriture non déclenchée.
- Arrêt : couple relu à **0** sur les 6 servos, port follower fermé. Port leader jamais ouvert. `lsof` : deux ports libres.
- **Aucun mouvement commandé.**

## Constats

- `wrist_flex` du follower est resté à 103 depuis 22:20 (sonde de consigne). Cette position est à 12 pas de `range_min` = 91 enregistré dans la calibration : le poignet repose quasiment en butée basse de sa plage calibrée.
- `Goal_Velocity` = 0 : sur Feetech STS, 0 signifie vraisemblablement « vitesse maximale » (**ASSUMED**). Cela confirme que l'activation du couple avec `Goal_Position = 0` sans recalage aurait produit un mouvement à pleine vitesse.

## Suite

Le contrôle a fonctionné comme prévu. Pour une nouvelle tentative, sur un **nouveau GO** :
- follower **hors couple** : ramener **à la main** `wrist_flex` vers le milieu de sa plage (≈ 1250 brut, plage 91..2414) ;
- vérifier la position par une lecture seule ;
- relancer le même lanceur.

Le décalage d'environ 70° sur `wrist_flex` entre les deux bras (ASSUMED) fera probablement échouer la concordance des poses (≤ 5°) : à mesurer d'abord en lecture seule, les deux bras en pose concordante.

## Essai 2 — 2026-10-06 22:50:41 CEST — ABORTED avant activation du couple

- GO HQ ; le poignet du follower avait été recentré à la main selon l'opérateur.
- Même lanceur (sha256 `c5baac1c…`) ; calibrations inchangées (`974f819f…`, `f48d50d5…`) ; ports libres.
- Contrôles statiques, IDs 1..6 (modèle 777), couple initial 0, registres == fichier : OK.
- **Abandon** : `ABORT[follower_precheck]: follower wrist_flex present 101 outside [91+20, 2414-20]`.
- Recalage, activation du couple, leader et boucle : **non atteints**. Écritures : 6 × `Torque_Enable = 0` (arrêt sûr). Couple relu à 0 ×6, port fermé ; port leader jamais ouvert.
- Journal : `2026-10-06T225041-first-teleop.events.json`, sha256 `a787847447bebe4ae357448741a7907d735755ae4aff863118c40eb86e8cc104`.

### Lecture

`wrist_flex` du follower : 1570 (22:10) → 103 (22:20) → 103 (22:46) → **101 (22:50)**.
- **ASSUMED** : couple à 0, le poignet **retombe par gravité** contre sa butée basse, qui correspond à peu près au `range_min` calibré (91). Un recentrage à la main ne tient pas sans support.
- À 101, la position est **dans** les limites du servo (91..2414). La marge de 20 du lanceur est un choix conservateur de l'agent, pas une contrainte du servo.

### Options (décision HQ, nouveau GO requis)

1. **Caler physiquement** le poignet du follower vers le milieu de sa course (cale, support) pendant le démarrage. Après l'activation du couple, le servo tient la position recalée. Aucun changement de code. Ne pas tenir le poignet à la main au moment de l'activation : risque de pincement.
2. **Réduire la marge** du contrôle de plage pour `wrist_flex`, par exemple à 5 (101 ≥ 96). Changement de code à relire : le servo tiendrait alors sa position en butée basse.
3. Revoir la calibration du follower : `range_min` = 91 sur `wrist_flex` traduit la butée, ce qui est cohérent.

## Essai 3 — 2026-10-06 22:56:13 CEST — marge `wrist_flex` = 5 — ABORTED à la concordance des poses (après activation du couple, avant toute consigne)

- **Changement autorisé (GO HQ)** : marge de démarrage par articulation ; `wrist_flex` = 5, autres = 20. Le diff ne touche que cette constante et les deux contrôles de plage. Lanceur sha256 `b7195fc1ef69caba27e029110345089df29329f614074bc2a7095395769e4e9b`. Essai à blanc OK.
- Calibrations inchangées (`974f819f…`, `f48d50d5…`).
- Journal : `2026-10-06T225613-first-teleop.events.json`, sha256 `5f99fe6683f5155d77c2bf29e63b1d2fc1674a2eb20b0421aec224f74586cb2a`. `…steps.jsonl` vide : aucune itération de boucle.

### Recalage de la consigne — PROVEN

| Moteur | Goal avant | Écrit | Relu | Présent | Mouvement depuis le précheck |
|---|---|---|---|---|---|
| shoulder_pan | 0 | 2085 | 2085 | 2085 | 0 |
| shoulder_lift | 0 | 2024 | 2024 | 2024 | 0 |
| elbow_flex | 0 | 2047 | 2047 | 2047 | 0 |
| wrist_flex | 0 | 101 | 101 | 101 | 0 |
| wrist_roll | 0 | 951 | 951 | 951 | 0 |
| gripper | 0 | 2140 | 2140 | 2140 | 0 |

### Activation du couple du follower — PROVEN sans à-coup

- `Torque_Enable = 1` et `Lock = 1` sur les 6 servos (phase `follower_torque_enable`), **après** le recalage vérifié.
- Dérive dans les 0,5 s qui suivent : **0 pas sur les 6 servos**. Le follower a tenu sa position. **Première activation du couple du follower ; aucun mouvement brusque.**

### Écritures (toutes dans la liste blanche ; garde non déclenchée)

- Follower `configure` : 40=0, 55=0, 7=0, 85=254, 41=254, 33=0, P/D/I 16/32/0, pince 16=500, 28=250, 36=25. `Phase` (18) non réécrit : bit 4 déjà à 0.
- Recalage : 42 ×6. Activation : 40=1, 55=1 ×6.
- Leader `configure` : 40=0, 55=0, 7=0, 85=254, 41=254, 33=0. Couple du leader **jamais** activé.
- Arrêt : 40=0 ×6 sur chaque bras. Couple **relu à 0** ×6 sur les deux bras ; ports fermés.

### Concordance des poses — ÉCHEC (garde voulue)

| Articulation | Follower | Leader | Écart |
|---|---|---|---|
| shoulder_pan | 2,1° | 8,0° | −5,9° |
| shoulder_lift | −2,1° | −0,1° | — (≤ 5) |
| elbow_flex | −0,0° | −0,1° | — |
| wrist_flex | **−101,2°** | −0,1° | **−101,1°** |
| wrist_roll | **−96,4°** | 2,2° | **−98,6°** |
| gripper | 7,3 % | 1,6 % | +5,8 % |

- `wrist_flex` : le follower repose en butée basse par gravité (brut 101) ; le leader est au milieu.
- `wrist_roll` : environ 98° d'écart entre les deux bras.
- On ne peut pas savoir si cela vient des **poses physiques** ou d'un **décalage entre les deux calibrations** sans une mesure en pose volontairement concordante.

**RESULT = ABORTED** à `pose_match`. Aucune consigne de téléop envoyée ; le suivi de `shoulder_pan` n'est pas testé.
