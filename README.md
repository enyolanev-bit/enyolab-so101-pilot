# enyolab-so101-pilot

## Démarrage rapide — téléopération leader → follower SO-101

| Fonction | Statut |
|---|---|
| **Téléopération leader → follower** (`scripts/teleop_official.py`) | **PROVEN** le 2026-10-07 : suivi fluide confirmé par l'opérateur ; couple du follower relu à 0 après chaque session |
| **Dessin par rejeu** : enregistrer au leader, rejouer au follower (`scripts/drawing_library.py`) | **PROVEN** le 2026-10-07 ; choix par Astra testé hors ligne seulement |
| Dessin autonome génératif avec Astra (`boris/`) | **EXPÉRIMENTAL** : voir la dernière section |

### Matériel requis

- Un bras **follower SO-101** (servos STS3215, alimentation **12 V**) et un bras **leader SO-101**, chacun avec sa carte contrôleur USB.
- Un Mac (macOS, Apple Silicon testé) et deux câbles USB de données.
- L'interrupteur de l'alimentation 12 V **à portée de main** : c'est l'arrêt d'urgence.
- Optionnel, seulement pour le dessin : caméras InnoMaker U20CAM-1080p (outil) et U20CAM-720P (contexte).

### Logiciel

- **Python 3.12** et **LeRobot 0.6.1** (extras `core_scripts`, `feetech`, `kinematics`), épinglés dans `uv.lock`.
- Gestionnaire [`uv`](https://docs.astral.sh/uv/) ≥ 0.12.13 (`brew install uv`).

```sh
git clone https://github.com/enyolanev-bit/enyolab-so101-pilot.git
cd enyolab-so101-pilot
uv sync --locked --python 3.12        # crée .venv avec LeRobot 0.6.1
```

### 1. Identifier les ports USB

Branche le **follower** et le **leader**, puis :

```sh
ls /dev/cu.usbmodem*
.venv/bin/python -m serial.tools.list_ports -v
```

| Bras | Port attendu | Numéro de série USB |
|---|---|---|
| follower | `/dev/cu.usbmodem5B7B0152071` | `5B7B015207` |
| leader | `/dev/cu.usbmodem5B7B0154401` | `5B7B015440` |

Sur macOS, le nom du port dérive du numéro de série : avec ces deux cartes, il reste identique d'un Mac à l'autre. Si un numéro diffère, **ne lance rien** et vérifie le matériel.

### 2. Installer les deux fichiers de calibration

Les calibrations sont propres à ces deux bras. Elles ne sont **pas** dans Git et sont remises séparément par ENYOLAB.

```sh
mkdir -p ~/.cache/huggingface/lerobot/calibration/robots/so_follower \
         ~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader
cp follower_nevil.json  ~/.cache/huggingface/lerobot/calibration/robots/so_follower/
cp pilot001_leader.json ~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/
shasum -a 256 ~/.cache/huggingface/lerobot/calibration/robots/so_follower/follower_nevil.json \
              ~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/pilot001_leader.json
# follower_nevil.json  03b26c3328b557d69b5146d5f316b5f23b760dd13fe7341d7e0b3ebe6b6425c9
# pilot001_leader.json 183455cd72f827f5084fed6127a2397bff45615f5897cda53276d97e663f5e41
```

Le script de téléopération refuse de démarrer si l'empreinte du follower diffère. Ne lance jamais `lerobot-calibrate` sans l'accord d'ENYOLAB.

### 3. Lancer la téléopération leader → follower

1. Mets les deux bras dans une **pose proche**, par exemple en « L ». Au démarrage, le follower rattrape la pose du leader.
2. Si la pince du follower tient un objet, mets la poignée du leader dans la même ouverture : la pince copie la poignée.
3. Allume le 12 V du follower, garde la main près de l'interrupteur, et dégage la zone autour du follower.

```sh
TELEOP_MAX_REL=5 TELEOP_FPS=30 .venv/bin/python scripts/teleop_official.py 300    # 300 s
```

- **Avant le couple :** le script vérifie que le couple du follower est à 0, recale chaque consigne sur la position réelle (évite un départ brusque), puis lance `lerobot-teleoperate` (LeRobot officiel).
- **Pendant la session :** chaque pas est limité à 5°, à 30 Hz.
- **À la fin :** le couple est coupé, puis relu à 0 sur les 6 servos.
- **Réglages plus lents :** `TELEOP_MAX_REL=2 TELEOP_FPS=15`. Plafonds : 5° par pas, 30 Hz, 1800 s.
- **Refus avant tout couple** si une calibration manque ou a la mauvaise empreinte, ou si un port USB ne correspond pas.
- **Codes de sortie :** 0 = OK ; 1 = `lerobot-teleoperate` en échec (couple vérifié à 0) ; 2 = refus avant démarrage ; 3 = couple non confirmé à 0, **couper le 12 V**.
- **Test hors ligne** du script, sans matériel : `.venv/bin/python scripts/test_teleop_official_offline.py`.

### 4. Dessiner avec Astra : enregistrer au leader, rejouer au follower

| Fonction | Statut (2026-10-07) |
|---|---|
| Enregistrer un dessin fait au leader (`record`) | **PROVEN** (dataset LeRobot de 2699 images, 90 s) |
| Rejouer ce dessin au follower (`replay`) | **PROVEN** : même tracé confirmé par l'opérateur |
| Prompt → Astra choisit le dessin → rejeu (`draw`) | Chemin **testé hors ligne** (API simulée) ; **appel réel NOT_PROVEN** (plus de crédit) |

```sh
.venv/bin/python scripts/drawing_library.py record bridge --description "simple Golden Gate bridge"
.venv/bin/python scripts/drawing_library.py list
.venv/bin/python scripts/drawing_library.py replay bridge
.venv/bin/python scripts/drawing_library.py draw "dessine un pont du Golden Gate"    # 1 appel Astra
.venv/bin/python scripts/drawing_library.py draw "..." --offline-astra --dry-run     # sans API ni moteur
```

- **Enregistrement :** il démarre au premier mouvement du leader et s'arrête après 5 s d'immobilité (90 s max par défaut). La pince du follower reste fermée, car la poignée du leader ne se lit pas.
- **Rejeu :** le follower doit partir de la **pose « L »**, pointe en l'air, avec la feuille **au même endroit** que lors de l'enregistrement. Une approche (≤ 5° par pas) mène à la pose de départ, puis la trajectoire est rejouée à 5° par pas maximum, et le couple est vérifié à 0 à la fin.
- **Astra** (`OPENAI_API_KEY` dans `boris/.env`) reçoit le prompt et la liste des dessins (nom et description). Il ne peut que **choisir un dessin enregistré ou refuser** : aucune valeur moteur ne vient du modèle.
- **Données :** les dessins vont dans `data/drawings/`, ignoré par Git. Ils dépendent de la calibration et de la position de la feuille ; ceux de démonstration sont remis à part.
- **Tests hors ligne :** `.venv/bin/python scripts/test_drawing_library_offline.py`.

### Arrêt d'urgence

1. **Couper l'alimentation 12 V** : ça marche toujours. Le bras retombe : prévois de l'espace dessous.
2. `Ctrl+C` dans le terminal : LeRobot coupe le couple à la déconnexion.
3. Si une articulation part dans un sens inattendu, coupe le 12 V d'abord.

**Limite connue :** sur l'épaule, le coude et le poignet, la calibration des deux bras couvre toute la course. Un saut de lecture à ±180° de la pose « milieu » reste théoriquement possible. Ne replie pas le leader à fond.

### Dessin / peinture autonome (EXPÉRIMENTAL)

`boris/` contient le pipeline prompt → Astra → commande de dessin validée → contrôleur borné : `boris/run_boris.py`, guide dans `boris/README_BORIS.md`. **Statut au 2026-10-07 :**

- **Obtenu avec l'ancienne calibration du follower** (avant le 2026-10-07, donc à revalider) :
  - un premier trait autonome (confirmé par l'opérateur) ;
  - un pont reconnaissable, **une seule fois** (planificateur local, sans Astra, confirmé par l'opérateur) ;
  - une commande Astra valide, exécutée par le bras.
- **NOT_PROVEN** :
  - le dessin de bout en bout avec Astra, dont le résultat physique était une **feuille vierge** ;
  - un dessin répétable : contact pinceau/papier non maîtrisé, et cinématique URDF en désaccord d'environ 90° avec l'orientation observée.
- `boris/controller.py` vérifie l'**ancienne** empreinte de calibration du follower. Il refuse de démarrer tant qu'elle n'est pas revalidée après la recalibration du 2026-10-07.

Les preuves de chaque essai sont dans `evidence/` (rapports `2026-10-0*-*.md`).

---


Couche de livraison et d'expérimentation du système **SO-101 leader / follower** pour le pilote **Boris × Astra Paint**.

Ce dépôt est volontairement **propre, indépendant et partageable**. Il ne remplace pas `lab-hardware`.

| Dépôt | Rôle |
|---|---|
| `lab-hardware` | historique, R&D, traces, preuves d'audit — **reste privé** |
| `enyolab-so101-pilot` | environnement de livraison du pilote — **destiné à être partagé** |

---

## Historique — état au 2026-10-05 (PÉRIMÉ, conservé pour la traçabilité)

> **Cette section est dépassée.** L'état actuel est celui du « Démarrage rapide » en haut de cette page :
> téléopération leader → follower **PROVEN** le 2026-10-07, les deux bras recalibrés le 2026-10-07.
> Les mentions ci-dessous (« leader non calibré », « téléopération NOT_PROVEN », etc.) décrivent le 2026-10-05.

Cet état provenait de l'audit en lecture seule **ENYO-14**. Rien n'y était affirmé sans artefact.

### PROVEN

- Un **artefact de calibration follower** existe, contient les entrées de **6 moteurs**, et a été préservé hors machine.
- La source mécanique amont est identifiée et épinglée : `TheRobotStudio/SO-ARM100` @ `fda892cba81032c46c40976a48c9ceadbf40a9ca`.
- Le matériel du second bras est commandé et payé (voir ENYO-13).

### TO_REVALIDATE

- **Validité physique de la calibration follower sur le robot actuellement assemblé.**
  L'artefact existe ; rien ne démontre qu'il corresponde encore à l'état mécanique présent du bras.

### NOT_PROVEN

- calibration **leader** — aucun artefact retrouvé ;
- **téléopération physique** ;
- **dataset physique** enregistré ;
- **policy physique** ;
- **rollout physique**.

### PROVEN — logiciel, et identification matérielle sans mouvement (Mac ENYOLAB)

- LeRobot **0.6.1** (`lerobot[core_scripts,feetech]`, décision HQ, ENYO-14) installé dans l'environnement dédié du dépôt (`.venv`, Python 3.12, `uv.lock`) sur le **Mac ENYOLAB** (hôte de bring-up). Validation **logicielle** uniquement : version, imports SO-101, Feetech, PyAV, TorchCodec, OpenCV, modules dataset et `lerobot-record`, présence des commandes. Aucun port série ouvert, aucune commande LeRobot exécutée. Non installé sur le Mac de Boris. Artefacts : `evidence/2026-10-05-lerobot-0.6.1-software-validation.md`, `evidence/2026-10-05-record-stack-validation.md`.
- Caméra **poignet** InnoMaker U20CAM-1080P (Mac ENYOLAB, session du 2026-10-05) : identité **prouvée par contenu d'image** (corrélation 0,999 avec la capture par nom) à l'index OpenCV 0 ; capture 640×480, 28,88 fps mesurés, encodage AV1, relecture PyAV et TorchCodec OK. Ordre AVFoundation instable ; stabilité de l'index OpenCV **non mesurée** : reconfirmer par contenu d'image à chaque session. Artefact : `evidence/video/2026-10-05-wrist-camera-capture.md`.
- Ports série sur le Mac ENYOLAB, hub actuel : leader / follower identifiés par débranchement contrôlé (geste opérateur, énumération par l'agent). Artefact : `evidence/2026-10-05-serial-port-identification.md`.

### PROVEN — amont (documentation), conformité physique non relevée

- Réduction par articulation, leader et follower : doc officielle LeRobot `v0.6.1`. Références Cxxx **déduites** via la nomenclature SO-ARM100. Voir [`docs/hardware.md`](docs/hardware.md).

### NOT_CONNECTED

- caméra **dessus** (U20CAM-720P) — la cible du pilote reste poignet + dessus.

### UNKNOWN

- conformité physique des bras assemblés à l'affectation amont (marquage des servos non relevé) — voir [`docs/hardware.md`](docs/hardware.md) ;
- architecture Raspberry Pi (productisation future, hors Pilote #001) — voir [`docs/architecture.md`](docs/architecture.md) ;
- état physique réel du bras leader, dont la pièce `Trigger_SO101` est en cours de réimpression (ENYO-6).

> (2026-10-05) Aucune ligne n'affirmait alors que le leader était calibré ni que la téléopération fonctionnait. Remplacé par le Démarrage rapide.

---

## Expérience cible

Cible : Boris travaille **uniquement depuis son Mac**, sans Jetson, sans Raspberry Pi, sans les dépôts historiques ENYOLAB et sans recherche manuelle de dépendances.

### Disponible aujourd'hui — installation + scripts en lecture seule

Prérequis machine : Mac **Apple Silicon (arm64)** avec [Homebrew](https://brew.sh). Voir [`setup/mac.md`](setup/mac.md).

```bash
brew install uv ffmpeg           # uv >= 0.12.13 ; FFmpeg systeme requis par TorchCodec
git clone <url>
cd enyolab-so101-pilot
uv sync --locked --python 3.12   # environnement .venv épinglé : LeRobot 0.6.1, figé par uv.lock
./scripts/check_system.sh        # OS, CPU, Python, LeRobot du .venv, FFmpeg, périphériques USB
./scripts/find_ports.sh          # liste les ports série candidats, sans les ouvrir
./scripts/test_cameras.sh        # liste les caméras et leurs index AVFoundation, sans capture
```

Les trois scripts n'ouvrent aucun port, n'envoient aucune commande et ne font bouger aucun moteur. **Attention** : `uv sync` rend aussi disponibles les commandes LeRobot (`lerobot-calibrate`, `lerobot-teleoperate`, `lerobot-record`…), qui, elles, **ne sont pas bloquées** et agissent sur le robot. Ne les lancer qu'avec un GO HQ explicite. Après installation, consigner dans `evidence/` la version de LeRobot et le hash de `uv.lock` (critère de sortie de [`setup/mac.md`](setup/mac.md)).

> **Ports série :** sur macOS, le nom `/dev/cu.usbmodem<numéro de série>1` dérive du numéro de série de la carte ; avec les deux cartes de ce pilote il est le même sur tout Mac (ASSUMED, vérifié par `scripts/teleop_official.py`, qui refuse si le numéro ne correspond pas). **Index caméra** : propres à chaque Mac (voir `boris/README_BORIS.md`).

### Scripts volontairement bloqués

```bash
./scripts/teleop.sh                      # BLOCKED (historique) — utiliser scripts/teleop_official.py
./scripts/record_demo.sh --task drawing  # BLOCKED — enregistrement de dataset non validé
```

Ces deux scripts **se terminent immédiatement avec un code de sortie non nul**, par construction (`AGENTS.md`). La téléopération validée le 2026-10-07 passe par `scripts/teleop_official.py` (Démarrage rapide). L'enregistrement (`docs/recording.md`) reste **NOT_PROVEN**.

---

## Tâches

`tasks/drawing.md`, `tasks/folding.md`, `tasks/freeform.md` décrivent **l'expérience visée**, pas des capacités démontrées. Aucune de ces tâches n'a été exécutée sur le robot physique.

---

## Avant toute mise sous tension

Lire [`docs/safety.md`](docs/safety.md). Sans exception.

---

## Contenu du dépôt

| Chemin | Contenu |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Pilote #001 = Mac direct ; Pi 4 = candidat futur, `RASPBERRY_PI_ARCHITECTURE = TO_BE_VALIDATED` ; place de la Jetson |
| [`docs/hardware.md`](docs/hardware.md) | bras, servos, carte, alimentation, caméras, pièces imprimées — avec le niveau de preuve par ligne |
| [`docs/safety.md`](docs/safety.md) | à lire avant toute mise sous tension |
| [`docs/recovery.md`](docs/recovery.md) | que faire quand quelque chose ne va pas |
| [`docs/recording.md`](docs/recording.md) | brouillon de la commande `lerobot-record` (non exécutée) |
| [`setup/mac.md`](setup/mac.md) | hôte du Pilote #001 ; `LEROBOT_VERSION = 0.6.1` — installé (Mac ENYOLAB, logiciel seulement) |
| [`setup/raspberry-pi.md`](setup/raspberry-pi.md) | productisation future, `PLANNED` — rien n'a été installé ni mesuré |
| [`setup/jetson.md`](setup/jetson.md) | infrastructure ENYOLAB, non prêtée à Boris ; le pilote n'en dépend pas |
| [`config/robot.example.yaml`](config/robot.example.yaml) | gabarit, valeurs `CHANGEME` |
| [`config/cameras.example.yaml`](config/cameras.example.yaml) | gabarit, valeurs `CHANGEME` |
| [`calibration/README.md`](calibration/README.md) | rôle des fichiers de calibration, état constaté, règles |
| [`tasks/`](tasks/README.md) | dessin / pliage / libre — expérience visée, **NOT_PROVEN** |
| [`scripts/teleop_official.py`](scripts/teleop_official.py) | **téléopération leader → follower validée** (+ `scripts/test_teleop_official_offline.py`, tests hors ligne) |
| [`boris/`](boris/README_BORIS.md) | dessin / Astra — **EXPÉRIMENTAL** |
| `scripts/so_paint_pilot.py` | **NON SUPPORTÉ** : dépend d'un dépôt `so-paint` séparé, absent d'ici ; refuse de tourner sans `SO_PAINT_REPO` |
| [`hardware/side-camera-mount/`](hardware/side-camera-mount/README.md) | support imprimable de la caméra latérale (OpenSCAD, STL, 3MF Bambu X2D) — dimensions ASSUMED |
| `evidence/` | artefacts de preuve versionnés (métadonnées, logs) ; médias bruts conservés en local, ignorés par Git |

Aucun fichier de calibration n'est versionné ici. `.gitignore` ignore `calibration/*.json` et `boris-handoff/` : c'est volontaire. Les deux fichiers de calibration approuvés sont remis à part (Démarrage rapide, étape 2).

---

## Pour les agents

Tout agent travaillant dans ce dépôt lit d'abord [`AGENTS.md`](AGENTS.md).
