# AGENTS.md — règles de travail dans ce dépôt

Ces règles s'appliquent à **tout agent** — Claude Code, Codex, Cursor, ou autre — qui travaille dans `enyolab-so101-pilot`. Elles priment sur l'habitude et sur l'envie d'avancer vite.

Ce dépôt pilote un **robot physique**. Une erreur ici ne casse pas un build : elle casse une pièce, un servo, ou une main.

---

## 1. Evidence first

Aucune affirmation sans artefact. Un fichier, un log, une mesure, une photo horodatée, un hash.
Un commentaire de code disant qu'une étape a fonctionné **n'est pas une preuve**.
Un nom de fichier **n'est pas une preuve**.
Le souvenir d'une session précédente **n'est pas une preuve**.

## 2. Distinguer PROVEN / ASSUMED / PLANNED / UNKNOWN

Chaque énoncé d'état porte son niveau :

| Niveau | Sens |
|---|---|
| **PROVEN** | un artefact vérifiable existe, et il est cité |
| **ASSUMED** | plausible, non vérifié — doit être marqué comme tel |
| **PLANNED** | prévu, pas encore fait |
| **UNKNOWN** | non déterminé — et c'est une réponse acceptable |

Ne jamais promouvoir un ASSUMED en PROVEN sans la vérification qui le justifie.

## 3. Aucun mouvement moteur sans autorisation explicite

Pas de téléopération, pas de homing, pas de couple appliqué, pas de `torque_enable`, sans un GO humain explicite pour **cette** action, dans **cette** session. Une autorisation passée ne vaut pas pour la suivante.

## 4. Aucune calibration automatique

La calibration engage l'intégrité mécanique du bras. Aucun agent ne lance `lerobot-calibrate`, n'écrit ni n'écrase un fichier de calibration de sa propre initiative.

## 5. Aucune opération Git destructive

Interdits : `git reset --hard`, `git clean`, `git checkout -- .`, `git push --force`, réécriture d'historique, suppression de branche. En cas de doute sur l'état du dépôt : **s'arrêter et demander**.

## 6. Aucun secret, aucun chemin machine personnel commité

Pas de token, pas de clé, pas de mot de passe, pas de SSID. Pas de chemin absolu du type `/Users/<nom>/…` dans un fichier versionné. Les fichiers de calibration spécifiques à une machine ne sont **jamais** commités sans revue HQ.

## 7. Aucun dataset, policy ou téléop déclaré réussi sans artefact

« Ça a marché » n'est pas un résultat. Un dataset se prouve par ses épisodes, une policy par son checkpoint et son évaluation, une téléop par un log ou une vidéo. Sans cela : **NOT_PROVEN**.

## 8. La sécurité précède le mouvement

Avant toute mise en mouvement : lire `docs/safety.md`, vérifier la zone dégagée, savoir où couper l'alimentation, et s'assurer qu'un humain est présent. Jamais de premier mouvement sans surveillance directe.

## 9. S'arrêter sur toute ambiguïté matérielle

Un port série inattendu, deux adaptateurs identiques, un servo qui ne répond pas, une tension incertaine, un ID moteur en doublon : **on s'arrête**. On documente ce qu'on voit, on ne devine pas. Un ID moteur attribué au mauvais servo peut rendre un bras inutilisable.

---

## Ce qui est bloqué par construction

`scripts/teleop.sh` et `scripts/record_demo.sh` sortent en erreur volontairement. Un agent **ne les débloque pas** pour faire avancer une tâche : le déblocage est une décision humaine documentée, accompagnée des artefacts qui la justifient.
