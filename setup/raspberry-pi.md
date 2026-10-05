# Setup — Raspberry Pi 4

**Statut : `PLANNED`. Rien n'est installé, rien n'est configuré, rien n'est vérifié.**

## Pourquoi un Raspberry Pi

L'architecture cible du pilote Boris ne doit pas dépendre de la Jetson, qui est la plateforme historique ENYOLAB. Un Pi 4 est envisagé comme hôte local des deux bras et des caméras. Voir [`../docs/architecture.md`](../docs/architecture.md).

**`RASPBERRY_PI_ARCHITECTURE = TO_BE_VALIDATED`** — cette architecture est une **candidate**, pas une solution en service.

## État constaté lors d'ENYO-14

`PI4_READY_STATE = UNKNOWN`

- aucun `~/.ssh/config` ;
- aucune résolution mDNS pour `raspberrypi.local` ou `pi.local` ;
- aucune trace dans `known_hosts` ni dans la table ARP.

Je ne peux pas distinguer « aucun Pi » de « Pi éteint ». Les deux hypothèses restent ouvertes.

## À déterminer avant toute installation

| Question | Pourquoi elle bloque |
|---|---|
| Le Pi existe-t-il physiquement ? | tout le reste en dépend |
| OS et architecture (64 bits ?) | conditionne la disponibilité des roues Python |
| Version de Python disponible | LeRobot impose un plancher |
| LeRobot est-il installable sur cette plateforme, et dans quelle version ? | **point dur** — voir `mac.md` |
| Le Pi tient-il le débit de deux bus servo + deux caméras USB ? | non démontré, à mesurer |
| Alimentation : le Pi et les bus servo sont-ils alimentés séparément ? | mélanger les alimentations est une source classique de brown-out |

## Ce qui n'est pas décidé

Rien. Ni l'OS, ni la version, ni la topologie USB, ni l'alimentation. Toute page de ce dépôt qui affirmerait le contraire serait à corriger.
