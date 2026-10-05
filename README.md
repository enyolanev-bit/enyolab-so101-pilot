# enyolab-so101-pilot

Couche de livraison et d'expérimentation du système **SO-101 leader / follower** pour le pilote **Boris × Astra Paint**.

Ce dépôt est volontairement **propre, indépendant et partageable**. Il ne remplace pas `lab-hardware`.

| Dépôt | Rôle |
|---|---|
| `lab-hardware` | historique, R&D, traces, preuves d'audit — **reste privé** |
| `enyolab-so101-pilot` | environnement de livraison du pilote — **destiné à être partagé** |

---

## État du système — au 2026-10-05

Cet état provient de l'audit lecture seule **ENYO-14**. Rien n'y est affirmé sans artefact.

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

### PROVEN — logiciel seulement

- LeRobot **0.6.1** (décision HQ, ENYO-14) installé dans l'environnement dédié du dépôt (`.venv`, Python 3.12, `uv.lock`) sur le **Mac ENYOLAB** (hôte de bring-up). Validation **logicielle** uniquement : version, imports SO-101 et Feetech, présence des commandes. Aucune exécution matérielle. Non installé sur le Mac de Boris. Artefact : `evidence/2026-10-05-lerobot-0.6.1-software-validation.md`.
- Ports série sur le Mac ENYOLAB, hub actuel : leader / follower identifiés par débranchement contrôlé (geste opérateur, énumération par l'agent). Artefact : `evidence/2026-10-05-serial-port-identification.md`.

### PROVEN — amont (documentation), conformité physique non relevée

- Réduction par articulation, leader et follower : doc officielle LeRobot `v0.6.1`. Références Cxxx **déduites** via la nomenclature SO-ARM100. Voir [`docs/hardware.md`](docs/hardware.md).

### UNKNOWN

- conformité physique des bras assemblés à l'affectation amont (marquage des servos non relevé) — voir [`docs/hardware.md`](docs/hardware.md) ;
- architecture Raspberry Pi (productisation future, hors Pilote #001) — voir [`docs/architecture.md`](docs/architecture.md) ;
- état physique réel du bras leader, dont la pièce `Trigger_SO101` est en cours de réimpression (ENYO-6).

> Aucune ligne de ce dépôt n'affirme que le leader est calibré, ni que la téléopération fonctionne.

---

## Expérience cible

### Disponible aujourd'hui — lecture seule, sans risque

```bash
git clone <url>
cd enyolab-so101-pilot
./scripts/check_system.sh     # OS, CPU, Python, LeRobot, périphériques USB
./scripts/find_ports.sh       # liste les ports série candidats, sans les ouvrir
./scripts/test_cameras.sh     # liste les caméras détectées, sans capture
```

Ces trois scripts n'ouvrent aucun port, n'envoient aucune commande et ne font bouger aucun moteur.

### Bloqué aujourd'hui — à débloquer après validation

```bash
./scripts/teleop.sh                      # BLOCKED
./scripts/record_demo.sh --task drawing  # BLOCKED
```

Ces deux scripts **se terminent immédiatement avec un code de sortie non nul**. C'est voulu : ils resteront bloqués tant que la téléopération et l'enregistrement n'auront pas été validés avec artefacts à l'appui.

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
| [`setup/mac.md`](setup/mac.md) | hôte du Pilote #001 ; `LEROBOT_VERSION = 0.6.1` — installé (Mac ENYOLAB, logiciel seulement) |
| [`setup/raspberry-pi.md`](setup/raspberry-pi.md) | productisation future, `PLANNED` — rien n'a été installé ni mesuré |
| [`setup/jetson.md`](setup/jetson.md) | infrastructure ENYOLAB, non prêtée à Boris ; le pilote n'en dépend pas |
| [`config/robot.example.yaml`](config/robot.example.yaml) | gabarit, valeurs `CHANGEME` |
| [`config/cameras.example.yaml`](config/cameras.example.yaml) | gabarit, valeurs `CHANGEME` |
| [`calibration/README.md`](calibration/README.md) | rôle des fichiers de calibration, état constaté, règles |
| [`tasks/`](tasks/README.md) | dessin / pliage / libre — expérience visée, **NOT_PROVEN** |
| `evidence/` | vide — destiné aux artefacts de preuve (logs, mesures, photos) |

Aucun fichier de calibration n'est versionné ici. `.gitignore` ignore `calibration/*.json` : c'est volontaire.

---

## Pour les agents

Tout agent travaillant dans ce dépôt lit d'abord [`AGENTS.md`](AGENTS.md).
