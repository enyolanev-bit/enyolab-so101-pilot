# Support caméra latérale — Boris

Support imprimable pour la 3e caméra (`side_camera`, InnoMaker U20CAM-720P) : posé sur la table à côté de la feuille, objectif à environ 2 cm au-dessus de la table, tourné vers la pointe du pinceau.

## Concept : « berceau à rails »

La carte caméra glisse **par le haut** dans deux rails rainurés montés sur un petit socle. Pas de vis dans la carte, donc pas besoin de connaître l'entraxe des trous de fixation. Le câble est bridé au socle par un collier passé dans deux fentes, il ne tire donc pas sur la carte.

| Version | Pièces | Angle | Quincaillerie |
|---|---|---|---|
| **v1** (recommandée aujourd'hui) | 1 | fixé à l'impression : `v1_tilt0`, `v1_tilt10`, `v1_tilt20` | 1 collier de serrage |
| v2 | 2 (`v2_base` + `v2_cradle`) | réglable à la main, tenu par friction | 2 vis M3×10 + 1 collier |

## Hypothèses de dimensions

| Grandeur | Valeur | Statut |
|---|---|---|
| Carte | 32 × 32 mm | ASSUMED (fiche revendeur, non mesurée) |
| Épaisseur de carte | 1,6 mm (rainure 2,0 mm) | ASSUMED |
| Objectif | centré sur la carte (`lens_off_z = 0`) | ASSUMED (vu sur photo) |
| Connecteur | au dos, près d'un bord : la lèvre arrière ne recouvre que 1,2 mm | ASSUMED |
| Centre optique | 22 mm au-dessus de la table (v1), 24 mm (v2) | PLANNED |
| Plongée | 0 / 10 / 20° (v1), libre (v2) | PLANNED |

**À mesurer au pied à coulisse avant une v2 propre :** largeur et hauteur de la carte, épaisseur de la carte, hauteur du centre de l'objectif depuis le bord bas, position et hauteur du connecteur au dos, épaisseur de la plaque plexi sous la feuille.

Les ajustements se font dans le bloc `[Caméra — À MESURER]` du `.scad`. Si la carte flotte dans les rails, passer `slot_clear` à 0.3 ; si elle force, à 0.6. Si le connecteur bute, baisser `back_cover`.

## Générer les STL

```sh
openscad -D 'part="v1"' -D tilt=10 -o stl/v1_tilt10.stl side_camera_mount.scad
openscad -D 'part="v2_base"'   -o stl/v2_base.stl   side_camera_mount.scad
openscad -D 'part="v2_cradle"' -o stl/v2_cradle.stl side_camera_mount.scad
openscad -D 'part="v2_assembly"' -D tilt=15 side_camera_mount.scad   # aperçu
```

## Impression

- **Matériau : PETG HF**, la bobine déjà chargée. Le PLA conviendrait aussi ; changer de bobine n'apporte rien ici.
- **Orientation :** v1 et `v2_base` à plat, socle sur le plateau, telles qu'exportées. `v2_cradle` debout, traverse sur le plateau.
- **Supports : aucun.** Les rails penchent au plus de 20° et les trous M3 horizontaux font 3,4 mm.
- Profil `0.24mm Standard @BBL X2D`, buse 0,4, 2 parois, remplissage 15 %, plaque Textured PEI.

Projets slicés dans `print/` (Bambu Studio CLI, 2026-10-07, X2D 0.4 + Bambu PETG HF) :

| Plateau | Temps estimé | Filament |
|---|---|---|
| `v1_tilt10_PETG-HF_X2D.3mf` | 27 min 18 s | 9,11 g / 2,96 m |
| `v1_tilt10+tilt20_PETG-HF_X2D.3mf` | 42 min 56 s | 18,25 g / 5,93 m |

| `v1_tilt10+tilt20_PETG-HF_X2D_tree-support.3mf` (supports arbre auto activés) | 42 min 59 s | 18,25 g |

Avec les supports arbre en mode auto (seuil 35°), le slicer ne génère **aucun** support : les seules faces orientées vers le bas penchent de 10 ou 20° par rapport à la verticale (analyse des STL). Ce sont des estimations du slicer, pas une durée d'impression mesurée. La plaque Textured PEI est ASSUMED : si une autre plaque est installée, la changer dans Bambu Studio avant de lancer.

## Montage et réglage

1. Faire glisser la carte par le haut dans les rails, objectif vers l'avant (côté sans socle), jusqu'à la butée basse. Si elle a du jeu, ajouter une bande de scotch ou une pointe de pâte adhésive dans une rainure.
2. Faire descendre le câble derrière la carte et le brider au socle avec un collier passé dans les deux fentes, en laissant une boucle lâche entre le collier et la carte.
3. Poser le support **hors de la feuille**, avant de la plaque plexi contre le bord, objectif à **6 à 10 cm** de la zone de contact visée. Le fixer avec du double-face ou de la pâte adhésive sous le socle, puis marquer l'emplacement au scotch.
4. v2 : serrer les deux vis M3 jusqu'à ce que le berceau tienne seul sa position, régler l'angle à la main, puis resserrer un quart de tour.

## Vérifier le cadrage (sans moteur)

Poser un pinceau **à la main** sur la feuille au point visé, puis capturer une image avec `side_camera`. Le cadrage est bon si l'image montre :
- les poils et la pointe nets,
- la ligne papier/pointe vers le tiers inférieur de l'image,
- 1 à 3 cm de papier autour,
- et, quand on soulève le pinceau à la main de quelques millimètres, l'espace visible sous la pointe.

Si le papier occupe trop l'image, passer à un angle plus faible. S'il n'apparaît presque pas, passer à un angle plus fort.

## Points à vérifier avant d'imprimer

- [ ] La carte mesure bien environ 32 × 32 mm (sinon modifier `pcb_w` et `pcb_h`).
- [ ] Le connecteur au dos est à plus de 1,2 mm du bord latéral.
- [ ] L'emplacement prévu est hors de l'enveloppe de mouvement du bras : le haut du support est à 34 mm de la table.
- [ ] Le socle ne passe pas sous la plaque plexi et n'entre pas dans le champ (son bord avant est aligné sur l'avant des rails).
