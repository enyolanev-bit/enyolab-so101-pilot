# Setup — macOS

**Hôte principal du Pilote #001 Boris** (architecture Mac direct, voir [`../docs/architecture.md`](../docs/architecture.md)) : bras et caméras en USB sur le Mac de Boris, LeRobot exécuté localement. Statut : **PLANNED** — rien n'est installé chez Boris.

## État

**Rien n'est installé par ce dépôt.** Aucun venv n'est créé, aucune dépendance n'est posée. Cette page documente ce qui est constaté et ce qui reste à décider.

## Version LeRobot — `LEROBOT_VERSION_STATUS = UNDETERMINED`

**Aucune version n'est retenue à ce stade, et ce n'est pas un oubli.**

Règle : la version LeRobot est **explicitement épinglée et validée sur la cible de déploiement réellement utilisée** pour la session. Pour le Pilote #001, cette cible est le **Mac de Boris**. La Jetson et le Raspberry Pi ne sont pas dans le chemin d'exécution du pilote et ne conditionnent pas ce choix.

| Cible | Version constatée | Statut |
|---|---|---|
| **Mac de Boris** (cible Pilote #001) | — | **UNKNOWN** — non installé, non relevé |
| Mac ENYOLAB | 0.5.1 (wheel) | PROVEN — relevé lors de l'audit ENYO-14 |
| Jetson (infrastructure ENYOLAB) | 0.6.1 *annoncé* | ASSUMED — non vérifié, machine hors ligne lors de l'audit |
| Raspberry Pi 4 (productisation future) | — | UNKNOWN — aucune installation constatée |

Choisir une version sans l'avoir validée sur la cible reviendrait à épingler un chiffre sur une hypothèse.

**Critère de sortie** : une version est épinglée, installée et validée sur le Mac de Boris, et elle est écrite ici avec la date et la raison du choix. « Validée » = artefacts consignés dans `evidence/` (version affichée par le gestionnaire de paquets, hash du lockfile), et calibrations utilisées produites sous cette même version. Si une autre machine entre plus tard dans la chaîne (rejeu, entraînement), elle s'aligne sur la version avec laquelle le dataset a été enregistré.

## Constaté sur le Mac ENYOLAB lors d'ENYO-14

- Python 3.12
- gestionnaire de paquets `uv` (ni conda, ni poetry, ni pyenv)
- LeRobot 0.5.1 installé en wheel, dans un environnement **non rattaché au SO-101**
- support SO-101 présent sous les modules génériques `robots/so_follower` et `teleoperators/so_leader` — aucun chemin littéral « so101 »
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
