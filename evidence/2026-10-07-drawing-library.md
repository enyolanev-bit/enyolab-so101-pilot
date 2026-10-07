# Bibliothèque de dessins : enregistrement au leader, rejeu au follower, choix par Astra — 2026-10-07

- **GO** : opérateur, étape 1 (enregistrement et rejeu avec Astra).
- **Script** : `scripts/drawing_library.py`. Bras et dataset gérés par LeRobot 0.6.1 ; la boucle de rejeu est celle de `lerobot-replay`. Mêmes gardes que la téléopération : calibrations et ports USB vérifiés, consigne recalée sur la position présente avant le couple, couple vérifié à 0 à la fin.

| Essai | Résultat |
|---|---|
| `lerobot-record` officiel, 60 s | Leader **constant** pendant toute la fenêtre : l'opérateur n'était pas prêt, et le follower a lâché le pinceau à cause de la pince (poignée du leader lue à 92 % en permanence). Mis de côté. |
| Boucle LeRobot avec pince maintenue, 60 s | Leader constant, problème de synchronisation : l'opérateur ne voit pas le terminal. Mis de côté. |
| **Lecture seule du leader**, 25 s | Base, épaule, coude et poignet **varient** ; la **poignée reste figée** (brut 3146). |
| **Enregistrement déclenché par le mouvement** | **2699 images, 90 s.** Base −58 à 13°, épaule 0 à 162°, coude −73 à 0°, poignet −2 à 89°, rotation 2 à 42°. Pince maintenue à 2,6 %. Couple relu à 0 ×6. Opérateur : « des traits, mais pas un pont ». |
| Rejeu n° 1 | Follower parti d'une épaule à +157° ; l'approche à 2°/pas ne soulève pas le bras → arrêt avant le rejeu, couple relu à 0. |
| **Rejeu n° 2** (follower remis en L, approche à 5°/pas) | **Rejeu complet, 90 s, couple relu à 0 ×6. « Même tracé » : confirmé par l'opérateur.** |
| Prompt → Astra → rejeu | **Non exécuté** : plus de crédit Astra. Chemin testé hors ligne (réponse API simulée et sélecteur hors ligne). |

## Tests hors ligne

- `scripts/test_drawing_library_offline.py` : **23/23**. Contrat Astra, vrai dataset LeRobot écrit puis relu, ordre de la séquence de rejeu, pince maintenue, déclenchement au mouvement, appel API simulé.
- `scripts/test_teleop_official_offline.py` : 14/14.

## Données

`data/drawings/bridge/` (160 Ko) et `library.json` sont ignorés par Git ; une copie est dans la remise privée `boris-handoff/drawings/`. Les enregistrements ratés sont dans `data/drawings/_discarded/` (locaux).
