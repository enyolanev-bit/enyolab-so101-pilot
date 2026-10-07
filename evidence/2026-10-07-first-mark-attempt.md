# Premier trait autonome sur papier — 2026-10-07 10:48 CEST — BLOCKED (erreur de bus au démarrage, couple jamais activé)

- **GO** : HQ, `shoulder_pan` +3°, sans retour. Pas d'Astra, pas de `wrist_flex`, aucune autre articulation.
- Avant le couple, l'opérateur a confirmé : pointe du marqueur en contact léger avec le papier, trajectoire dégagée, présence, coupure 12 V à portée.
- **Commande** : `boris/demo_move.py move --joint shoulder_pan --delta 3 --go`.
  - `controller.py` sha256 `92264cd6…` ; `demo_move.py` `14955b29…`.

## Déroulé (session `20261007T104855`)

- Lecture seule préalable OK : pose brute 2034 / 2019 / 982 / 2275 / 936 / 2072, couple 0.
- Contrôle préalable de la session : OK (pose 2034 / 2019 / 981 / 2275 / 936 / 2072).
- `configure()`, puis recalage : 6 consignes écrites (2034, 2019, 981, 2275, 936, 2072) et relecture des consignes OK.
- Relecture groupée de la position présente pour vérifier le recalage : **`Incorrect status packet!` 3 fois de suite** (`num_retry = 2`) → faute.
- **Couple jamais activé** : aucune écriture `Torque_Enable = 1` au journal. **Aucun mouvement commandé.**
- **Arrêt** : `Torque_Enable = 0` ×6, **relu à 0** ×6, port fermé.

## Résultats

- **Mouvement mesuré de `shoulder_pan`** : **0** (essai non atteint).
- **Dérive des autres articulations** : aucune, couple jamais actif.
- **Couple** : relu à 0 ×6.
- **VISIBLE_MARK_ON_PAPER** : HUMAN_CONFIRMATION_REQUIRED. Aucun trait n'est attendu, puisque le bras n'a pas reçu de consigne de mouvement.

## Lecture

- **Deuxième faute de bus en 20 minutes, toutes deux pendant le recalage** :
  - 10:30 : absence d'accusé sur l'écriture de la consigne du servo 5 ;
  - 10:48 : 3 lectures groupées de suite en échec.
- Entre les deux, 200 lectures groupées sur 200 et un essai complet ont réussi.
- Le bus est **intermittent** ; cause **UNKNOWN** (connecteur ou câble de la chaîne des servos, alimentation 12 V, port USB).
- La règle d'abandon a fonctionné deux fois avant toute mise sous couple.
- **Pas de nouvelle tentative automatique.** Recommandation à HQ : mesurer la fiabilité du bus en lecture seule (par exemple 2000 lectures groupées, en manipulant doucement les câbles), réensemencer les connecteurs des servos 4, 5 et 6 et du contrôleur, puis relancer le même trait.

| Fichier | sha256 |
|---|---|
| `boris/2026-10-07-demo-move-20261007T104856830982.json` | `2214918e…a2d0` |
| `boris/2026-10-07-session-20261007T104855616514-51131.jsonl` | `5ec2ef11…7d43` |
