# Identification des ports série leader / follower

- **Date** : 2026-10-05, 21:19 → 21:28 CEST
- **Hôte** : Mac ENYOLAB, adaptateurs branchés sur un hub USB 2.1
- **Outil** : `./scripts/find_ports.sh` uniquement (énumération de `/dev/cu.*`, **aucun port ouvert**). `lerobot-find-port` n'a **pas** été exécuté.
- **Geste physique** : débranchement puis rebranchement du câble USB du **leader**, fait par un opérateur humain ; l'agent n'a fait que relancer l'énumération.

## Séquence

| Heure (CEST) | État physique | `usbmodem5B7B0152071` | `usbmodem5B7B0154401` |
|---|---|---|---|
| 21:19:17 | les deux adaptateurs branchés | présent | présent |
| 21:26:26 | USB du leader débranché | présent | **absent** |
| 21:28:19 | USB du leader rebranché, même hub | présent | **présent** |

Les deux adaptateurs se présentent tous deux comme `USB Single Serial` (ioreg) : seule cette séquence les distingue.

## Sorties brutes de `find_ports.sh` (bloc « PORTS SERIE CANDIDATS »)

21:19:17 CEST — les deux adaptateurs branchés :

```text
  /dev/cu.Bluetooth-Incoming-Port          (systeme / Bluetooth — ignorer)
  /dev/cu.debug-console                    (systeme / Bluetooth — ignorer)
  /dev/cu.JBLTune720BT                     (a identifier)
  /dev/cu.RedmiBuds6Lite                   (a identifier)
  /dev/cu.usbmodem5B7B0152071              <== CANDIDAT adaptateur servo
  /dev/cu.usbmodem5B7B0154401              <== CANDIDAT adaptateur servo
```

21:26:26 CEST — USB du leader débranché :

```text
  /dev/cu.Bluetooth-Incoming-Port          (systeme / Bluetooth — ignorer)
  /dev/cu.debug-console                    (systeme / Bluetooth — ignorer)
  /dev/cu.JBLTune720BT                     (a identifier)
  /dev/cu.RedmiBuds6Lite                   (a identifier)
  /dev/cu.usbmodem5B7B0152071              <== CANDIDAT adaptateur servo
```

21:28:19 CEST — USB du leader rebranché, même hub :

```text
  /dev/cu.Bluetooth-Incoming-Port          (systeme / Bluetooth — ignorer)
  /dev/cu.debug-console                    (systeme / Bluetooth — ignorer)
  /dev/cu.JBLTune720BT                     (a identifier)
  /dev/cu.RedmiBuds6Lite                   (a identifier)
  /dev/cu.usbmodem5B7B0152071              <== CANDIDAT adaptateur servo
  /dev/cu.usbmodem5B7B0154401              <== CANDIDAT adaptateur servo
```

Chaque exécution s'est terminée par « Termine. Aucun port ouvert. », exit 0.

## Résultat

- **Leader** = `/dev/cu.usbmodem5B7B0154401`
- **Follower** = `/dev/cu.usbmodem5B7B0152071`

## Limites

- Stabilité du nom vérifiée sur **un** rebranchement, sur le même hub. Non vérifiée : autre port USB, autre hub, redémarrage du Mac, Mac de Boris.
- L'identification repose sur la parole de l'opérateur pour le câble débranché (leader). Aucune photo.
- Ces ports sont propres à cette machine : ils ne valent pas pour le Mac de Boris.
