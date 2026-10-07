# Contrôleur Boris / Astra : construction et essais sans Astra — 2026-10-07

- **GO** : HQ, « BUILD PRACTICAL BORIS DRAWING CONTROLLER ».
- Opérateur présent, bras en vue. Il a confirmé avant le couple que la zone était dégagée et l'alimentation 12 V à portée (choix « +10 then return », puis « elbow_flex ±2° »).
- **Aucun appel à Astra ni à un modèle**, aucun crédit d'API consommé.
- Pas de leader (non branché), pas de dataset, pas de calibration.

## Fichiers (`boris/`, non commités)

- `controller.py` :
  - sha256 `6bfc0e797cdc00d8d1a2aa38067832eebd586d9745d563f27d61665cf4d7ab55` pendant les essais matériels ;
  - puis `27cd427c1d4c5098d0a235ab8005b8f12c658b66ecac524138aab77fd7a523fc`. La seule différence : la dérive des autres articulations est désormais remontée aussi en cas d'arrêt.
- `camera.py`, `capture_camera_by_id.swift` (copie identique de `scripts/`, sha256 `7a89e50c…`), `demo_move.py`, `sim_test.py`, `README_BORIS.md`, `requirements.txt`, `.env.example`, `.gitignore`.

## Contrôles hors ligne

`sim_test.py` (bus simulé, avec l'erreur statique mesurée du servo) : **29/29**. Couverture :

- mouvements nominaux dans les deux sens ;
- budgets d'excursion et de parcours ;
- refus : NaN, booléen, articulation non activée, pince ;
- pannes au démarrage : couple déjà actif, mauvais modèle de servo, registres ≠ fichier, activation partielle du couple, écriture interdite ;
- pannes en mouvement : dérive, sens inverse, absence de progrès, axe manquant, erreur de communication (alerte « couper le 12 V ») ;
- lecture seule sans aucune écriture ;
- arrêt par le chien de garde d'inactivité.

## Essais matériels (follower seul, pose de départ brute 2056 / 2021 / 2047 / 1370 / 938 / 2072)

| Session | Action | Résultat | Mesuré | Dérive des autres articulations | Arrêt |
|---|---|---|---|---|---|
| 09:47:15 | `check`, lecture seule | ROBOT_OK | IDs 1..6 = 777, couple 0, registres == fichier | – | **0 écriture** |
| 09:50:40 | `shoulder_pan` +10° | **MOVE_OK** | 2056 → 2171 : **+115 pas codeur = +10,11°** en 19 itérations, erreur finale −0,088° | 0,0 | couple relu à 0 ×6, port fermé |
| 09:51:03 | `shoulder_pan` −10° (retour) | **MOVE_OK** | 2171 → 2056 : **−115 pas codeur = −10,11°** en 18 itérations, erreur finale +0,088° | 0,0 | couple relu à 0 ×6, port fermé |
| 09:51:23 | `elbow_flex` +2° puis retour | **ARRÊT DE SÉCURITÉ** | 2047 → 2048 (+1 pas), consigne à 11 pas devant ; 3 itérations sans progrès | non enregistrée (défaut corrigé depuis) | couple relu à 0 ×6, port fermé |

Pour les trois sessions armées :

- maintien de 4 s : **0 pas** de dérive ;
- écritures conformes à la liste blanche :
  - `configure()` avec P = 16, D = 32, I = 0 ;
  - recalage de la consigne sur la position présente : 6 écritures, relues ;
  - couple à 1 uniquement au point autorisé ;
  - en mouvement : seulement des écritures groupées de position de consigne, chacune relue.
- **Note `elbow_flex`** : la session a été arrêtée avant la fin du mouvement, donc le résumé n'a pas enregistré la dérive des autres articulations (défaut corrigé depuis). La règle d'arrêt sur dérive est restée active pendant toute la session ; aucun arrêt pour dérive n'a eu lieu.

## Lecture

- **PROVEN (encodeurs)** : `shoulder_pan` à ±10° dans les **deux sens**, retour exact au brut de départ. L'avance de 6 pas codeur sur la consigne compense l'erreur statique (le servo s'arrête 4 à 6 pas avant sa consigne). Le dépassement mesuré est de 1 pas codeur au plus ; l'excursion mesurée est de 10,11° pour une borne de 10° (cible 114 pas, plus 1 pas de dépassement).
- **`elbow_flex` : BLOCKED.** Avec au plus 1° entre la consigne et la pose mesurée, le servo ne vainc pas sa charge ou son frottement (P = 16, I = 0). Le contrôleur s'est arrêté comme prévu.
  - Ni nouvelle tentative, ni changement de gain, ni augmentation de l'avance : ces options sont des **décisions HQ**.
- **Caméras** : capture par ID exact, la 1080p (`tool_camera`) et la 720p (`context_camera`), environ 1,4 s par image. `capture_for_astra()` testé : JPEG de 1280 px de côté maximum, âge de 0,23 s au retour.
  - La vue outil montre la pointe du pinceau au-dessus du papier.
  - La vue de contexte ne montre que le papier, sans bras ni pinceau.
- **Visuel** : mouvement physique non observé par l'agent ; **confirmation à l'opérateur**.

## Preuves (`evidence/boris/`)

| Fichier | sha256 |
|---|---|
| `2026-10-07-demo-check-20261007T094716590962.json` | `b5ccd14e…1949` |
| `2026-10-07-session-20261007T094715566087-15455.jsonl` | `929e0cff…b08093` |
| `2026-10-07-demo-move-20261007T095055053995.json` (pan +10) | `ff3be21f…5a61` |
| `2026-10-07-session-20261007T095040692183-17324.jsonl` | `4d341c0a…19f8` |
| `2026-10-07-demo-move-20261007T095117712618.json` (pan −10) | `1b00d226…af48` |
| `2026-10-07-session-20261007T095103809910-17757.jsonl` | `7a383f4f…e1ee` |
| `2026-10-07-demo-move-20261007T095129640292.json` (elbow, arrêt) | `61ec9f85…8440` |
| `2026-10-07-session-20261007T095123159168-17826.jsonl` | `06cee373…3f07` |
