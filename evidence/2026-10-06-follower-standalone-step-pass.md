# Premier mouvement autonome du follower — +1° `shoulder_pan`, sans leader — 2026-10-06 23:09:32 CEST — RÉSULTAT : PASS

- **GO** : HQ. Changement autorisé par rapport à l'essai de 23:04 : `num_retry=2` sur les **seules** relectures groupées de vérification (`sync_read`), soit 3 tentatives au maximum. Aucune relance sur les écritures. Le diff ne touche que 8 appels `sync_read` et le docstring.
  - Inchangé : la boucle de 6 tentatives d'écriture de `Torque_Enable = 0` à l'arrêt, déjà présente dans la version auditée.
- **Script** : `2026-10-06-follower_standalone_step.py`, sha256 `f2d5a935cd6334a39151be8197fc9374dc4c22c29d763ae16d677cd5349a7d93`. Essai à blanc OK.
- **Calibration** : `follower_nevil.json`, sha256 `f48d50d5…`, vérifiée.
- **Journaux** :
  - `2026-10-06T230932-follower-step.events.json`, sha256 `c082dd7242fc106cb562fdf1c81acb65908c7d15b946195a04b1e4f204d16372` ;
  - `2026-10-06T230932-follower-step.steps.jsonl`, sha256 `b1d84c63307eb026b9bad60d324fe9f16a44779b073207c363da090ba62bf9a6`.
- Pas de leader, pas de caméra, pas de dataset.

## Déroulé et mesures

| Étape | Résultat |
|---|---|
| Contrôles statiques, handshake, IDs 1..6 (777), couple 0, registres == fichier, plages | OK |
| Pose initiale (brut) | 2085 / 2024 / 2047 / 101 / 951 / 2140 |
| `Goal_Position` avant | égal à la position présente |
| Recalage (écrit / relu / mouvement) | égal partout, 0 mouvement sur les 6 servos |
| Activation du couple | 2026-10-06 23:09:33.110 ; 40=1 et 55=1 ×6 |
| Maintien 4 s (74 échantillons) | **dérive max = 0 pas** sur les 6 servos |
| Pose normalisée avant le pas | pan 2,066° ; lift −2,066° ; elbow −0,044° ; wrist_flex −101,231° ; roll −96,396° ; pince 7,346 % |
| Consigne demandée = envoyée | pan **3,066°** (+1,0°), autres articulations = pose actuelle ; borne `max_relative_target` 1.0 non dépassée |
| Envoi | **une seule** écriture groupée `Goal_Position` (adr. 42) |
| Trajectoire de `shoulder_pan` (échantillons de stabilisation, 1 s) | 2,066 → 2,154 → **2,681** (puis stable × 16) |
| Δ `shoulder_pan` | **+0,615°** (dans le bon sens ; dans [+0,3, +2,0]) |
| Dérive des autres articulations | **0,0** pour lift, elbow, wrist_flex, wrist_roll et pince |
| Arrêt | 40=0 ×6 ; couple **relu à 0** ×6 ; port fermé |

## Lecture

- **PROVEN** : le follower exécute une consigne autonome bornée, dans le bon sens, sans bouger les autres articulations. La séquence de démarrage sûre (recalage vérifié, puis couple) fonctionne de bout en bout.
- Sous-atteinte : +0,615° pour +1,0° demandé, soit 7 pas codeur sur ≈ 11. Cause probable (**ASSUMED**) : zone morte ou erreur statique avec le gain P = 16 de LeRobot, pour un si petit pas. Non bloquant ; à caractériser avant des consignes fines.
- `wrist_flex` a été tenu en butée basse (brut 101) pendant tout l'essai, sans dérive.
- Toutes les écritures sont dans la liste blanche ; aucune garde déclenchée ; aucune erreur de communication, ou relances de lecture absorbées sans trace d'échec.

**RESULT = PASS.** STOP après ce mouvement unique.
