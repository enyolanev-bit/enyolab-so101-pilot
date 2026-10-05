# Setup — macOS

**Hôte principal du Pilote #001 Boris** (architecture Mac direct, voir [`../docs/architecture.md`](../docs/architecture.md)) : bras et caméras en USB sur le Mac de Boris, LeRobot exécuté localement. Statut : **PLANNED** — rien n'est installé chez Boris.

## État

Le dépôt **définit** son environnement (`pyproject.toml` + `uv.lock`). Aucun script du dépôt n'installe quoi que ce soit automatiquement. Un `.venv` a été créé par `uv sync --locked --python 3.12` sur le **Mac ENYOLAB** (bring-up, logiciel seulement). **Rien n'est installé sur le Mac de Boris.**

Prérequis connus pour recréer l'environnement : **macOS arm64** (le `uv.lock` fige `torch` 2.11.0, dont le wheel macOS publié n'existe qu'en arm64), uv ≥ 0.12.13, Python 3.12.

## Version LeRobot — `LEROBOT_VERSION = 0.6.1`

`LEROBOT_VERSION_STATUS` : **installé sur le Mac ENYOLAB (bring-up), validation logicielle seulement** — **non installé sur le Mac de Boris**. Décision HQ (ENYO-14, 2026-10-05).

- **Version retenue** : `lerobot[feetech]==0.6.1`, Python 3.12.
- **Hôtes** (décision HQ) : bring-up = **Mac ENYOLAB** ; déploiement ultérieur = **Mac de Boris**.
- **Environnement** : `.venv` à la racine du dépôt, ignoré par Git, défini par `pyproject.toml` et figé par `uv.lock` (sha256 `a2c6fc5bd50c890f…`). Recréer à l'identique :

  ```bash
  uv sync --locked --python 3.12   # validé avec CPython 3.12.13, uv 0.12.13
  ```

- **Validé (logiciel)** — artefact : `evidence/2026-10-05-lerobot-0.6.1-software-validation.md`. Python 3.12.13 ; `lerobot` 0.6.1 ; import de `SO101Follower`/`SO101FollowerConfig` et `SO101Leader`/`SO101LeaderConfig` ; types `so101_follower` / `so101_leader` enregistrés ; `scservo_sdk` (`feetech-servo-sdk` 1.0.0) et `FeetechMotorsBus` importables ; commandes `lerobot-find-port`, `lerobot-setup-motors`, `lerobot-calibrate`, `lerobot-teleoperate`, `lerobot-record` présentes. **Aucune de ces commandes n'a été exécutée.**
- **Non validé** : tout comportement matériel ; `ffmpeg` (requis par `lerobot-record` pour l'encodage vidéo) non vérifié.
- **Ne pas modifier** `sample-efficient-imitation/.venv` (0.5.1, bac à sable ALOHA/simulation) : il n'est pas l'environnement du pilote.
- **Raison** (audit ENYO-14, lecture de sources, 2026-10-05) : types `so101_*`, attribut `name`, chemin de calibration, format JSON et méthode `calibrate()` relevés identiques entre le paquet 0.5.1 installé et le tag `v0.6.1` (commit `7e241bd6`) ; 0.6.1 est la version la plus récente sur PyPI au 2026-10-05 ; 0.6.1 ajoute les options `num_read_retries` et `position_{p,i,d}_coefficient`. Comportement réel de 0.6.1 : non vérifié.
- **Types CLI** : `--robot.type=so101_follower`, `--teleop.type=so101_leader`.

Règle : la version LeRobot est **explicitement épinglée et validée sur la cible de déploiement réellement utilisée** pour la session. Pour le Pilote #001, cette cible est le **Mac de Boris**. La Jetson et le Raspberry Pi ne sont pas dans le chemin d'exécution du pilote et ne conditionnent pas ce choix.

| Cible | Version constatée | Statut |
|---|---|---|
| **Mac de Boris** (cible Pilote #001) | — | **UNKNOWN** — non installé, non relevé ; architecture CPU UNKNOWN (arm64 requis par `uv.lock`) |
| Environnement dédié du dépôt (`.venv`) sur le Mac ENYOLAB | 0.6.1 | **PROVEN (logiciel)** — `evidence/2026-10-05-lerobot-0.6.1-software-validation.md`, aucune exécution matérielle |
| Mac ENYOLAB — `sample-efficient-imitation/.venv` (bac à sable, hors pilote) | 0.5.1 (wheel) | PROVEN — relevé lors de l'audit ENYO-14 |
| Jetson (infrastructure ENYOLAB) | 0.6.1 *annoncé* | ASSUMED — non vérifié, machine hors ligne lors de l'audit |
| Raspberry Pi 4 (productisation future) | — | UNKNOWN — aucune installation constatée |

Une installation validée logiciellement n'est pas une version validée sur la cible : la condition de version de `scripts/teleop.sh` reste non remplie.

**Critère de sortie** : 0.6.1 installé et validé **sur le Mac de Boris** (condition 4 de `scripts/teleop.sh`). Une validation dans un autre environnement ENYOLAB ne remplit pas cette condition. « Validée » = artefacts consignés dans `evidence/` (version affichée par le gestionnaire de paquets, hash du lockfile), et calibrations utilisées produites sous cette même version. Si une autre machine entre plus tard dans la chaîne (rejeu, entraînement), elle s'aligne sur la version avec laquelle le dataset a été enregistré.

## Constaté sur le Mac ENYOLAB lors d'ENYO-14

- Python 3.12
- gestionnaire de paquets `uv` (ni conda, ni poetry, ni pyenv)
- LeRobot 0.5.1 installé en wheel, dans un environnement **non rattaché au SO-101**
- support SO-101 présent sous les modules génériques `robots/so_follower` et `teleoperators/so_leader` ; types CLI enregistrés `so101_follower` et `so101_leader` (`config_so_follower.py` l.45, `config_so_leader.py` l.33 du paquet 0.5.1 installé)
- points d'entrée disponibles : `lerobot-find-port`, `lerobot-setup-motors`, `lerobot-calibrate`, `lerobot-teleoperate`, `lerobot-record`, `lerobot-train`

## Premier contact, sans risque

```bash
./scripts/check_system.sh
./scripts/find_ports.sh
./scripts/test_cameras.sh
```

Ces scripts sont en lecture seule. Ils n'ouvrent aucun port série.

## Points d'attention macOS

- Un câble USB-C de **charge** ne transporte pas les données. Si aucun port série n'apparaît après branchement de l'adaptateur, suspecter le câble avant la carte.
- macOS peut demander une autorisation d'accès à la caméra au premier usage. L'accorder depuis Réglages Système, pas depuis un script.
