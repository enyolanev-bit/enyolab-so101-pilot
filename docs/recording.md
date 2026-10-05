# Enregistrement d'un dataset — brouillon de commande

> **Statut : DRAFT, NON EXÉCUTÉ.** `lerobot-record` n'a jamais été lancé dans ce
> projet. La commande ci-dessous a été écrite à partir du **schéma source** de
> LeRobot 0.6.1 (`lerobot/scripts/lerobot_record.py`, `lerobot/configs/dataset.py`,
> `lerobot/configs/video.py`).
>
> **Rien ne la bloque techniquement.** Seul `scripts/record_demo.sh` est bloqué ;
> après `uv sync`, `lerobot-record` (comme `lerobot-calibrate` ou
> `lerobot-teleoperate`) est directement exécutable. **Ne pas lancer cette commande
> sans GO HQ explicite** et sans que toutes les conditions de `scripts/teleop.sh`
> soient remplies (AGENTS.md règles 3 et 4).

## Prérequis, tous à remplir sur la machine qui enregistre

- environnement : `uv sync --locked --python 3.12` (voir `../setup/mac.md`) ;
- FFmpeg système (`brew install ffmpeg`), exigé par TorchCodec selon le guide amont ;
- ports leader et follower **redécouverts sur cette machine** (`scripts/find_ports.sh` + débranchement contrôlé, voir `../evidence/2026-10-05-serial-port-identification.md`) ;
- index des caméras **redécouverts sur cette machine** puis **identité confirmée par comparaison de contenu avec une capture par nom**, index OpenCV ouverts un par un (méthode : `../evidence/video/2026-10-05-wrist-camera-capture.md`) : `scripts/test_cameras.sh` donne l'ordre AVFoundation (FFmpeg), dont la correspondance avec l'index OpenCV n'est **pas prouvée** et qui a changé d'une énumération à l'autre (`../evidence/video/2026-10-05-wrist-camera-capture.md`) ;
- calibrations `pilot001_follower` et `pilot001_leader` présentes et revalidées (voir `../calibration/README.md`) ;
- toutes les conditions de déblocage de `scripts/teleop.sh`.

## Commande cible (Pilote #001, poignet + dessus)

Les valeurs entre `<…>` sont **propres à la machine** et ne doivent jamais être copiées d'une autre. Les ids viennent du `config/robot.yaml` local (fixés par HQ pour le Pilote #001). À lancer **depuis la racine du dépôt** (le `--dataset.root` est relatif).

```bash
uv run lerobot-record \
  --robot.type=so101_follower \
  --robot.port=<PORT_FOLLOWER> \
  --robot.id=<ID_FOLLOWER> \
  --robot.max_relative_target=<VALEUR_FIXEE_PAR_HQ> \
  --robot.cameras="{ wrist: {type: opencv, index_or_path: <INDEX_POIGNET>, width: 640, height: 480, fps: 30}, overhead: {type: opencv, index_or_path: <INDEX_DESSUS>, width: 640, height: 480, fps: 30} }" \
  --teleop.type=so101_leader \
  --teleop.port=<PORT_LEADER> \
  --teleop.id=<ID_LEADER> \
  --dataset.repo_id=local/pilot001_drawing \
  --dataset.no_stamp=true \
  --dataset.root="data/pilot001_drawing_$(date +%Y%m%d_%H%M%S)" \
  --dataset.single_task="Draw the target shape on the sheet with the pen" \
  --dataset.num_episodes=10 \
  --dataset.episode_time_s=30 \
  --dataset.reset_time_s=20 \
  --dataset.fps=30 \
  --dataset.video=true \
  --dataset.rgb_encoder.vcodec=libsvtav1 \
  --dataset.streaming_encoding=true \
  --dataset.push_to_hub=false \
  --display_data=false
```

Pour la mise en route avec la seule caméra poignet, retirer l'entrée `overhead` de `--robot.cameras`.

> ⚠️ **Calibration déclenchée par la commande elle-même.** En 0.6.1, `lerobot-record`
> connecte le leader puis le follower avec calibration activée
> (`lerobot_record.py` l.459-460), sans option CLI pour la désactiver. Quand les
> moteurs ne correspondent pas au fichier de l'id, ou qu'il n'y a pas de fichier
> (`so_follower.py` l.99-103 et l.115-131, même logique dans `so_leader.py`) :
> - **fichier présent** : invite « ENTRÉE ou `c` ». **Toute réponse autre que `c`
>   — y compris ENTRÉE, `n`, `non`, `q` — réécrit la calibration du fichier dans
>   les moteurs.** `c` lance une calibration complète. **La seule façon de refuser
>   est Ctrl+C.**
> - **aucun fichier** : la calibration complète démarre directement. **Le couple
>   est coupé avant la première consigne** (`disable_torque`) : le bras peut
>   retomber sous son poids. Le tenir ou le poser en butée basse avant de lancer ;
>   Ctrl+C ne remet pas le couple.
>
> Ce sont des écritures de calibration (AGENTS.md règle 4) : **seul un humain
> autorisé poursuit.** Au 2026-10-05, `pilot001_follower.json` n'est **pas** actif
> (copie seulement stagée, TO_REVALIDATE) et aucune calibration leader n'existe :
> la commande déclencherait une calibration complète des deux bras.
>
> Les caméras ne sont ouvertes **qu'après** la calibration (`so_follower.py`
> l.105-106) : un index caméra faux ou non confirmé ne fait échouer la commande
> qu'après l'invite ou l'écriture de calibration. **Confirmer les index avant.**

## Choix et points d'attention (lus dans le code 0.6.1)

| Option | Pourquoi |
|---|---|
| `--robot.max_relative_target` | **Le défaut est `None` : aucune limite** au saut de position du follower entre deux pas. Sur un bras dont la calibration est TO_REVALIDATE, une borne est requise. Valeur à fixer par HQ (unité : celle des positions, en degrés avec `use_degrees=True`, le défaut). |
| `--dataset.push_to_hub=false` | **Le défaut est `True`** : sans cette option, le dataset est envoyé sur le Hub Hugging Face. |
| `--dataset.root=data/...` | Dataset écrit dans le dépôt, sous `data/`, qui est ignoré par Git. Ne **pas** déplacer `HF_LEROBOT_HOME` pour y arriver : cette variable déplace aussi le cache de calibration. |
| `--dataset.no_stamp=true` + root horodaté | Par défaut, `repo_id` reçoit un suffixe date-heure ; ici l'horodatage est porté par le dossier `root`, ce qui évite d'écraser une session précédente. |
| `--dataset.rgb_encoder.vcodec=libsvtav1` | Valeur par défaut de LeRobot 0.6.1, écrite explicitement. Disponible dans PyAV (`../evidence/2026-10-05-record-stack-validation.md`). |
| `--dataset.streaming_encoding=true` | Encodage pendant la capture, comme dans l'exemple amont ; non testé ici. |
| Backend caméra | Non précisé : OpenCV choisit (`ANY`). Les tests de ce dépôt utilisent `CAP_AVFOUNDATION` (valeur 1200) ; la signification d'un index peut différer selon le backend. Forcer le backend via la config caméra : syntaxe CLI **non vérifiée**. |
| `--teleop.*` obligatoire | `lerobot-record` refuse de démarrer sans téléopérateur. |
| `repo_id` sans préfixe `eval_` | Ce préfixe est réservé à l'évaluation de policy et rejeté par `lerobot-record`. |
| `num_episodes`, `episode_time_s`, `reset_time_s`, `single_task` | Valeurs de départ proposées pour la tâche dessin (voir `../tasks/drawing.md`), **à fixer par HQ**. Défauts amont : 50 épisodes, 60 s, 60 s. |

## Non vérifié

- Comportement réel de la commande (jamais exécutée).
- Tenue de 30 fps avec deux caméras et deux bus servo sur un même Mac.
- Index et ports sur le Mac de Boris.
