# Capture caméra poignet — InnoMaker U20CAM-1080P — RÉSULTAT : BLOCKED (identité non prouvée)

- **Date** : 2026-10-05, ~22:33 CEST
- **Hôte** : Mac ENYOLAB (bring-up), arm64, `.venv` du dépôt (LeRobot 0.6.1, `lerobot[core_scripts,feetech]`)
- **Accès matériel** : caméras uniquement, aucun port série ouvert, aucune commande LeRobot exécutée. **Intention** : n'ouvrir que la caméra poignet. **Constat** : il n'est **pas prouvé** que le périphérique ouvert par OpenCV (index 1) était l'InnoMaker ; il a pu s'agir de la caméra intégrée du MacBook (voir « Identité du périphérique »).

## Identification du périphérique

Première énumération AVFoundation, ~22:30 CEST (`ffmpeg -f avfoundation -list_devices true -i ""`, sans ouverture de flux) :

| Index AVFoundation | Périphérique |
|---|---|
| 0 | Caméra du MacBook Pro (intégrée — non retenue) |
| **1** | **Innomaker-U20CAM-1080p-S1** (`system_profiler` : UVC VendorID 3141 / ProductID 25446) |
| 2 | Caméra Desk View du MacBook Pro |
| 3-5 | Capture screen 0-2 |

**Index OpenCV de l'InnoMaker : UNKNOWN.** L'ordre AVFoundation **n'est pas stable** :

| Énumération (`ffmpeg -list_devices`) | `[0]` | `[1]` |
|---|---|---|
| ~22:30 CEST (avant capture) | Caméra du MacBook Pro | Innomaker-U20CAM-1080p-S1 |
| ~22:36 CEST (`scripts/test_cameras.sh`, après capture) | Innomaker-U20CAM-1080p-S1 | Caméra du MacBook Pro |

## Identité du périphérique — contre-vérifications

| Capture | Résultat |
|---|---|
| OpenCV `VideoCapture(1, CAP_AVFOUNDATION)`, 5 s (ci-dessous) | 149 images, pièce sombre mais visible (luminance moyenne ≈ 4,7/255 ; plafonnier et LED rouge discernables) |
| FFmpeg **par nom** `Innomaker-U20CAM-1080p-S1`, 1 image, 2 essais (~22:34 CEST) | image noire (négociation de format de pixel) |
| FFmpeg **par nom**, 3 s, `uyvy422` 640×480 @ 29,58 fps (~22:37 CEST) | 89 images, **luminance 0,0** sur la première, la médiane et la dernière : **entièrement noir** |

Lecture : l'InnoMaker adressée **par son nom** ne renvoie que du noir, alors que la capture OpenCV « index 1 » montre une scène. Deux hypothèses restent ouvertes, aucune n'est tranchée :
1. la capture OpenCV index 1 venait de la **caméra intégrée du MacBook** (ordre des index différent entre OpenCV et FFmpeg, ou changé entre-temps) ;
2. l'InnoMaker est obturée (cache d'objectif, objectif contre une surface, obscurité totale) et l'index 1 était bien elle, avec une différence d'exposition entre OpenCV et FFmpeg.

Voyant vert de la caméra du MacBook pendant la capture OpenCV : **non observé (UNKNOWN)**.

**Confirmation humaine requise avant tout usage** : vérifier l'objectif de l'InnoMaker, éclairer la scène, puis refaire une capture **par nom** et une capture OpenCV en observant le voyant vert du MacBook (allumé = caméra intégrée ouverte).

Les index sont propres à chaque machine et, constat ici, **instables sur une même machine** : à redécouvrir à chaque session, sur le Mac de Boris comme ici.

## Capture

Script : OpenCV `VideoCapture(1, CAP_AVFOUNDATION)`, 1 s de préchauffe (comme `warmup_s=1` de LeRobot), 5 s d'acquisition, encodage PyAV `libsvtav1` (codec RGB par défaut de LeRobot 0.6.1), relecture PyAV + TorchCodec.

| Mesure | Valeur |
|---|---|
| Demandé | 640×480 @ 30 fps, 5 s |
| Rapporté par le driver OpenCV | 640×480 @ 30 fps |
| Obtenu | **640×480** |
| Images capturées | **149** |
| FPS mesuré | **29,74** |
| Codec MP4 | **AV1** (`libsvtav1` à l'encodage, `libdav1d` / TorchCodec `av1` au décodage), yuv420p |
| `wrist_capture.mp4` | 10 705 octets, sha256 `ecc19ff032f3e0be42bf02af6512d080c7396c2e4aefa9a39307ebaded15e3e1` |
| `wrist_still.png` (image du milieu) | 151 032 octets, sha256 `c3f2469f6a70888289be0eedcf6d4d0c619ac0ded3ebee8a22a22e4e94866ad8` |
| Relecture PyAV | 149 images décodées, 640×480 |
| Relecture TorchCodec 0.11.1 | 149 images, `av1`, 640×480, première image `[3, 480, 640]` |

**Chaîne capture → encodage AV1 → relecture PyAV/TorchCodec : fonctionnelle** (sur le périphérique effectivement ouvert).
**WRIST_CAPTURE = BLOCKED** : l'identité du périphérique capturé (InnoMaker poignet) n'est pas prouvée.

## Limites

- **Scène très sombre** (luminance moyenne ≈ 4,7 / 255) : qualité d'image pour un dataset **non évaluée** ; le faible poids du MP4 vient de cette scène presque uniforme.
- Mise au point manuelle non réglée.
- Médias bruts (`wrist_still.png`, `wrist_capture.mp4`) : **LOCAL_ONLY** (Mac ENYOLAB, `evidence/video/`), conservés **en local uniquement** (ignorés par Git : images de la pièce). Seules ces métadonnées sont versionnées.
- Avertissement macOS au chargement : classes Objective-C `AVFFrameReceiver` / `AVFAudioReceiver` définies en double (`libavdevice` embarqué par `av` et par `cv2`, plus FFmpeg Homebrew). Sans effet observé sur cette capture ; impact sur une session longue **non évalué**.
