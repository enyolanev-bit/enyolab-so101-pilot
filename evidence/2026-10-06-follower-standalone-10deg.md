# Mouvement autonome visible du follower — +10° sur `shoulder_pan` vers une consigne FIXE, sans leader — 2026-10-06 23:24:03 CEST

- **ENCODER_RESULT : BLOCKED.** Arrêt à la limite des 20 itérations, erreur finale **+0,505°** pour une tolérance de 0,5°.
- **HUMAN_VISUAL_CONFIRMATION : REQUIRED.** L'agent ne déclare pas de PASS visuel.

## Références

- **GO** : HQ, un seul essai de +10° à consigne fixe.
- **Script** : `2026-10-06-follower_standalone_10deg.py`, sha256 `32bc41dade7cb9f60ad082c61c60de4fd81a64588db0fc3a6ef420220ca320d5`.
  - Démarrage et fonctions utilitaires **identiques ligne pour ligne** au script 5 pas, vérifié par `diff`.
    - Inchangés : SHA de calibration, identité USB, registres, recalage `Goal_Position := Present_Position`, marge `wrist_flex` 5, `num_retry=2` sur les seules relectures, aucune relance sur les écritures, activation sûre du couple, maintien de 4 s, arrêt vérifié.
  - Seul le bloc de mouvement est nouveau.
  - Essai à blanc : refus sans `--go` ; contrôles statiques OK, puis échec propre sur port factice, 0 écriture.
- **Journaux** :
  - `2026-10-06T232403-follower-10deg.events.json`, sha256 `2ce2fce5edc02adc4268cadc5f0343aefff89a1ce18cf1774eba11804801d7be` ;
  - `2026-10-06T232403-follower-10deg.steps.jsonl`, sha256 `983e6e9e7bcfde04b746b2a25efb06878140a7f8ebb05631329f5d3f2d655ef7`.

## Démarrage

- Pose initiale (brut) : 2123 / 2024 / 2047 / 101 / 951 / 2140.
- Recalage : écrit = relu = présent sur les 6 servos.
- Activation du couple : 23:24:04.332.
- Maintien de 4 s : dérive max **0 pas** sur les 6 servos.

## Consigne

- **START_SHOULDER_PAN** = 5,407° (brut 2123).
- **TARGET_SHOULDER_PAN** = **15,407°**, fixe : jamais redéfinie.

## Itérations

Consigne envoyée bornée par `max_relative_target` = 1,0. Attente 0,4 s.

| It. | Avant (°) | Envoyé (°) | Après (°) | Δ (°) | Brut | Pas codeur depuis le départ | Erreur (°) |
|---|---|---|---|---|---|---|---|
| 1 | 5,407 | 6,407 | 5,934 | +0,527 | 2129 | 6 | 9,473 |
| 2 | 5,934 | 6,934 | 6,462 | +0,527 | 2135 | 12 | 8,945 |
| 3 | 6,462 | 7,462 | 6,989 | +0,527 | 2141 | 18 | 8,418 |
| 4 | 6,989 | 7,989 | 7,429 | +0,440 | 2146 | 23 | 7,978 |
| 5 | 7,429 | 8,429 | 7,956 | +0,527 | 2152 | 29 | 7,451 |
| 6 | 7,956 | 8,956 | 8,571 | +0,615 | 2159 | 36 | 6,835 |
| 7 | 8,571 | 9,571 | 9,099 | +0,527 | 2165 | 42 | 6,308 |
| 8 | 9,099 | 10,099 | 9,626 | +0,527 | 2171 | 48 | 5,780 |
| 9 | 9,626 | 10,626 | 10,154 | +0,527 | 2177 | 54 | 5,253 |
| 10 | 10,154 | 11,154 | 10,681 | +0,527 | 2183 | 60 | 4,725 |
| 11 | 10,681 | 11,681 | 11,209 | +0,527 | 2189 | 66 | 4,198 |
| 12 | 11,209 | 12,209 | 11,648 | +0,440 | 2194 | 71 | 3,758 |
| 13 | 11,648 | 12,648 | 12,176 | +0,527 | 2200 | 77 | 3,231 |
| 14 | 12,176 | 13,176 | 12,791 | +0,615 | 2207 | 84 | 2,615 |
| 15 | 12,791 | 13,791 | 13,319 | +0,527 | 2213 | 90 | 2,088 |
| 16 | 13,319 | 14,319 | 13,846 | +0,527 | 2219 | 96 | 1,560 |
| 17 | 13,846 | 14,846 | 14,374 | +0,527 | 2225 | 102 | 1,033 |
| 18 | 14,374 | 15,374 | 14,901 | +0,527 | 2231 | 108 | **0,505** |
| 19 | 14,901 | 15,407 | 14,901 | 0,000 | 2231 | 108 | 0,505 |
| 20 | 14,901 | 15,407 | 14,901 | 0,000 | 2231 | 108 | 0,505 |

- **Déplacement total** : **+108 pas codeur** (2123 → 2231), soit **+9,494°** sur les +10° demandés.
- **Itérations** : 20, le maximum.
- **Dérive des autres articulations** (lift, elbow, wrist_flex, wrist_roll, pince) : **0,0** à chaque itération, maximum absolu 0,0.
- **Erreur finale** : **+0,505°**, au-dessus de la tolérance de 0,5° de **0,005°**, soit moins d'un pas codeur.
- **Sens** : toujours positif. Aucun recul, aucun dépassement : max 14,901° pour une cible à 15,407°.
- **Écritures** : 20 écritures groupées `Goal_Position` dans la boucle, une par itération. Toutes dans la liste blanche, aucune garde déclenchée, aucune erreur de communication.

## Arrêt

- Écriture `Torque_Enable = 0` ×6, **relu à 0** ×6.
- Port fermé ; le port du follower est libre (`lsof` vide).

## Lecture

- **PROVEN (encodeur)** : mouvement autonome monotone de +9,49° sur `shoulder_pan` seul, vers une consigne fixe, sans dérive des autres articulations.
- **Cause du BLOCKED** : erreur statique résiduelle. Aux itérations 19 et 20, la consigne envoyée est la cible exacte (15,407°), mais le servo reste à 2231 brut, 0,505° (environ 6 pas codeur) en dessous.
  - C'est la même sous-atteinte qu'aux essais à 1° et à 5 pas : environ 5 à 6 pas codeur de zone morte ou d'erreur statique, avec P = 16 et I = 0 (**ASSUMED**).
  - Avec la tolérance de 0,5° et la borne de 20 itérations fixées par le GO, la convergence n'était pas atteignable à moins d'un pas codeur près. Aucun critère n'a été modifié.
- **Visibilité** : environ 9,5° de rotation de la base. La confirmation visuelle revient à l'opérateur.

**ENCODER_RESULT = BLOCKED** (critère de convergence ≤ 0,5° manqué de 0,005°).
**HUMAN_VISUAL_CONFIRMATION = REQUIRED.**
