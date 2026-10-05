# Capture caméra poignet — InnoMaker U20CAM-1080P — identité PROVEN (session du 2026-10-05)

- **Hôte** : Mac ENYOLAB (bring-up), arm64, `.venv` du dépôt (LeRobot 0.6.1, `lerobot[core_scripts,feetech]`)
- **Accès matériel** : caméras uniquement. Aucun port série ouvert, aucune commande LeRobot exécutée, aucun servo.
- **Médias bruts** : **LOCAL_ONLY** (Mac ENYOLAB, `evidence/video/`, ignorés par Git — images de la pièce). Seules ces métadonnées sont versionnées.

## Résultat — essai 2, 22:53-22:54 CEST (cache d'objectif retiré)

| Champ | Valeur |
|---|---|
| Capture par nom (`Innomaker-U20CAM-1080p-S1`, FFmpeg AVFoundation, `uyvy422` 640×480 @ 30) | **PASS** — 89 images, luminance moyenne 125 (écart-type 45) : scène réelle, éclairée |
| **Index OpenCV de l'InnoMaker** (`CAP_AVFOUNDATION`), à 22:53 | **0** |
| Identité | **PROVEN pour cette session** — par contenu d'image, pas par ordre d'énumération |
| Résolution obtenue | **640×480** (demandé 640×480) |
| FPS | demandé 30 ; rapporté par le driver OpenCV 30,00003 ; **mesuré 28,88** (144 images, 5 s, après 1 s de préchauffe) |
| Codec MP4 | **AV1** (`libsvtav1` à l'encodage, yuv420p), décodé par `libdav1d` / TorchCodec `av1` |
| `wrist_capture.mp4` | 29 756 octets, sha256 `d6df24aa9013cf95992140d7f36774a4a80844b4cd4324ba84c2d40c6c320ef1` |
| `wrist_still.png` (image médiane) | 325 029 octets, sha256 `a215066e3d799cf06082835a2cdd5be941a582acaa498b03c1cafea779701853` |
| Relecture PyAV | 144 images, 640×480 |
| Relecture TorchCodec 0.11.1 | 144 images, `av1`, 640×480, première image `[3, 480, 640]` |

### Méthode d'identification

1. Capture **par nom** de périphérique, 3 s, image de référence.
2. Ouverture des index OpenCV **un par un** (jamais deux caméras ouvertes ensemble), 1,5 s chacun, une image chacun. Corrélation de Pearson avec la référence, en niveaux de gris redimensionnés à 160×120 (`cv2.resize`, interpolation par défaut `INTER_LINEAR`) :

| Index OpenCV | Résolution | Luminance | Corrélation avec la capture par nom |
|---|---|---|---|
| **0** | 640×480 | 125,3 | **0,999** |
| 1 | 640×480 | 128,3 | 0,119 (caméra du MacBook) |
| 2 | — | — | n'existe pas (OpenCV : « out device of bound (0-1) ») |

3. Capture de preuve 5 s sur l'index 0.
4. Contre-vérification **après** la capture : nouvelle capture par nom. Corrélation `wrist_still.png` ↔ nom-avant **0,999**, ↔ nom-après **0,839**, ↔ index 1 **0,119**. Le recul à 0,839 accompagne une baisse de luminance de la capture d'après (≈ 125 → 119) : la scène ou l'exposition a changé entre les deux captures. Ce n'est pas un signe d'identité faible : 0,839 reste très au-dessus de 0,119. L'image médiane du MP4 donne aussi 0,839 avec la capture par nom d'après. Le contrôle visuel montre la même scène sur l'image par nom et sur l'image de preuve. L'image est à l'envers : la caméra est probablement montée retournée, à vérifier au montage.

### Instabilité des index — constat

| Heure (CEST) | Ordre FFmpeg `-list_devices` : `[0]` / `[1]` |
|---|---|
| ~22:30 | MacBook / InnoMaker |
| ~22:36 | InnoMaker / MacBook |
| 22:53:20 | InnoMaker / MacBook |
| 22:53 (juste après les tests OpenCV) | MacBook / InnoMaker |

L'ordre FFmpeg change d'une énumération à l'autre. Sa correspondance avec l'index OpenCV **n'est pas prouvée** : à 22:53:20 les deux concordaient (InnoMaker en `[0]` / OpenCV 0), puis FFmpeg a inversé l'ordre juste après les tests OpenCV. **L'index OpenCV est donc à reconfirmer par contenu d'image à chaque session**, sur le Mac ENYOLAB comme sur le Mac de Boris. La stabilité de l'index OpenCV lui-même dans le temps n'a pas été mesurée.

## Historique — essai 1, 22:33-22:37 CEST : BLOCKED

- Cause **ASSUMED** (déclaration de l'opérateur, sans artefact) : le cache était encore sur l'objectif de l'InnoMaker. C'est cohérent avec la luminance 0,0 des captures par nom.
- La capture OpenCV « index 1 » de cet essai (149 images, 29,74 fps, pièce sombre ; fichiers renommés `*_2026-10-05T2233_unidentified.*`, sha256 MP4 `ecc19ff0…`) venait **vraisemblablement de la caméra intégrée du MacBook**. C'est ASSUMED fort : à l'essai 2, l'index 1 est la caméra du MacBook. La caméra intégrée a donc probablement été ouverte involontairement lors de l'essai 1.

## Limites

- Identité prouvée **pour la session du 2026-10-05 seulement**.
- Mise au point manuelle non réglée ; orientation de montage (image à l'envers) à vérifier.
- 28,88 fps mesurés avec une seule caméra, sans bus servo : la tenue à 30 fps en enregistrement réel n'est pas évaluée.
- Avertissement macOS au chargement (classes Objective-C dupliquées entre `av`, `cv2` et FFmpeg Homebrew) : sans effet observé, impact sur une session longue non évalué.
