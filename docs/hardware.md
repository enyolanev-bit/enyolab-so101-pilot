# Materiel

Etat au **2026-10-05**. Chaque ligne porte son niveau de preuve.

## 1. Bras

| Element | Valeur | Preuve |
|---|---|---|
| Modele | SO-101, variante **Standard** | PROVEN — decision HQ, archi arretee |
| Bras | 1 leader + 1 follower | PROVEN |
| Servos par bras | 6 | PROVEN |
| Variante servo | STS3215 gamme **7.4 V** (Standard), les deux bras | PROVEN — doc upstream SO-ARM100 |
| Alimentation bus servo | **5 V**, architecture Standard (voir §2) | DECISION HQ — sources amont rapportees, non archivees ici (voir §2) |
| Variante Pro / follower 12 V | **non utilisee** | PROVEN — decision HQ |

> « 7.4 V » est la tension nominale de la gamme servo STS3215 Standard, pas la
> tension du bloc retenu pour ce pilote. Pour ce pilote, le bloc est un **5 V**.
> Ne pas acheter de bloc 7.4 V sur la foi de ce nom.

### Repartition des servos — PAIRE COMPLETE (leader + follower = 12 unites)

Ces quantites portent sur **les deux bras ensemble**, pas sur un bras.

| Reference | Reduction | Qte pour la paire (sur 12) |
|---|---|---|
| Feetech STS3215 **C001** | 1:345 | 7 |
| Feetech STS3215 **C044** | 1:191 | 2 |
| Feetech STS3215 **C046** | 1:147 | 3 |
| **Total** | | **12** = 6 leader + 6 follower |

Repartition 7 / 2 / 3 issue de la nomenclature upstream, au niveau de la paire.
Affectation par articulation — **PROVEN amont** (`docs/source/so101.mdx` du tag LeRobot `v0.6.1` (commit `7e241bd6`), l.35-44 ; lu le 2026-10-05 via `raw.githubusercontent.com`, sha256 du fichier `e75acfb7…`) :

| Articulation | Leader | Follower |
|---|---|---|
| 1 shoulder_pan | 1:191 (C044) | 1:345 (C001) |
| 2 shoulder_lift | 1:345 (C001) | 1:345 (C001) |
| 3 elbow_flex | 1:191 (C044) | 1:345 (C001) |
| 4 wrist_flex | 1:147 (C046) | 1:345 (C001) |
| 5 wrist_roll | 1:147 (C046) | 1:345 (C001) |
| 6 gripper | 1:147 (C046) | 1:345 (C001) |

La doc amont donne la reduction ; la reference Cxxx en est **deduite** via la
correspondance reference ↔ reduction de la nomenclature SO-ARM100
(`README.md` l.76-78 et l.87, commit `fda892cb`) : C001 = 1/345, C044 = 1/191,
C046 = 1/147 ; lot leader = 1 x C001 + 2 x C044 + 3 x C046. Total paire 7 / 2 / 3,
coherent. **Conformite physique des
bras assembles a ce tableau : non relevee** — relever le marquage de chaque
servo a son articulation et le consigner dans `evidence/` avant teleoperation.
Voir `../config/robot.example.yaml`.

> Les trois references partagent le meme boitier et le meme connecteur. **Elles
> ne sont pas interchangeables** : la reduction determine couple et vitesse de
> l'articulation. Monter un C046 a la place d'un C001 donne un bras qui bouge et
> qui est faux. Verifier le marquage avant montage, puis consigner quel servo
> est a quelle articulation.

## 2. Carte et alimentation

| Element | Valeur | Preuve |
|---|---|---|
| Carte bus servo | Waveshare Bus Servo Adapter (A), WSH-SBS-01 | PROVEN |
| Connecteur alim carte | barillet DC **5.5 x 2.1 mm** | PROVEN — datasheet |
| Alimentation cible | **5 V / 4 A minimum**, un bloc par bras | DECISION HQ — tension : voir ci-dessous |
| Modele retenu | Mean Well **GST25E05-P1J** | PROVEN |
| Polarite | **centre positif** — suffixe `P1J` = 2.1 x 5.5 x 11 mm, C+ | PROVEN — datasheet constructeur |

**Tension d'alimentation de la carte — elements amont rapportes par la revue
HQ (ENYO-14).** Les pages sources ne sont pas encore archivees dans ce depot :
niveau de preuve ici = **rapporte HQ, citation primaire a joindre sous
`evidence/`**.

- la plage nominale couramment documentee pour la carte Waveshare est
  **9–12.6 V** ;
- la documentation Waveshare admet aussi des tensions de bus servo injectees
  plus basses, dont la zone **5–8.4 V** ;
- la sortie bus suit la tension servo fournie ;
- l'architecture **SO-101 Standard** est alimentee en **5 V** dans son ecosysteme
  amont.

Sur cette base, HQ retient 5 V pour l'architecture Standard. La regle reste :
**la tension fournie doit correspondre a l'architecture servo visee.** Standard
= 5 V. Pro / follower 12 V = autre architecture, autres servos, non utilisee ici.
Ne jamais brancher un bloc 12 V sur un bras Standard.

> **[A VERIFIER AVANT PREMIERE MISE SOUS TENSION]** — relire la documentation
> de la carte reellement en main et confirmer que la tension du bloc est dans la
> plage d'injection admise ; lire l'etiquette du bloc ; mesurer la tension du
> bus sous charge au premier essai et la consigner dans `evidence/`.

> ⚠️ **Polarite.** Un barillet inverse sur un bus servo detruit
> silencieusement. La polarite du GST25E05-P1J est prouvee par le suffixe de
> reference constructeur, pas par la couleur du cable. Si le bloc utilise est un
> autre modele, **mesurer au multimetre avant de brancher.**

## 3. Cameras

| Role | Modele | Resolution visee | Preuve |
|---|---|---|---|
| Poignet | InnoMaker **U20CAM-1080P** | 640x480 @ 30 fps | PROVEN pour l'identification du module |
| Dessus | InnoMaker **U20CAM-720P** | 640x480 @ 30 fps | PROVEN pour l'identification du module |

- UVC, aucun pilote a installer.
- PCB **32 x 32 mm**, 4 trous **M2**.
- **Mise au point manuelle** : flou au premier branchement est normal.
- `PILOT_REQUIREMENT: wrist + overhead` — le pilote retient deux vues : poignet
  (gros plan sur la pince et l'objet) et dessus (scene et position du bras).
  C'est un choix de ce projet, pas une regle generale de l'apprentissage par
  imitation.
- La webcam integree du portable n'est **pas** une des vues retenues.
- Une seule camera (poignet) suffit pour la mise en route et la validation de la
  teleoperation ; la vue de dessus reste requise pour le Pilote #001.
- Etat au 2026-10-05 : poignet detectee mais capture **BLOCKED** (identite du
  peripherique capture non prouvee, images noires par nom, index instable :
  `../evidence/video/2026-10-05-wrist-camera-capture.md`) ; dessus
  **NOT_CONNECTED**.

> Le support imprime correspondant est un **FORM_FACTOR_MATCH_ONLY** : l'entraxe
> du support et celui du module concordent sur les cotes relevees, mais aucune
> source upstream ne prouve explicitement que ce support est concu pour ce
> module. A confirmer par essai mecanique a sec, sans forcer les vis.

## 4. Pieces imprimees

Jeu de reference : **PRINT_SET_001** (leader + follower), gele en interne.

| Point | Etat |
|---|---|
| Jeu complet imprime et verifie | **NON** |
| Piece `Trigger_SO101` | retiree — premiere impression defaillante |
| Nouvelle preparation | 3MF prepare, **pas encore imprime** |

Reglages upstream pour les pieces SO-101 (source : `README.md` du depot
SO-ARM100, section SO-101) : **PLA+**, buse 0.4 mm, couche 0.2 mm, remplissage
**15 %**, supports partout mais en ignorant les pentes a plus de 45°, **aucun
support dans les trous de vis d'axe horizontal**.

> Cause racine de l'echec du `Trigger_SO101` : les supports etaient desactives
> alors que la piece comporte un plafond plat de ~578 mm² a 26 mm de hauteur.
> Il s'imprimait dans le vide. L'orientation, elle, etait correcte.

## 5. Visserie et assemblage

| Element | Etat |
|---|---|
| Servo horn 25T | **[A CONFIRMER]** |
| Cables 3 fils servo | **[A CONFIRMER]** |
| Visserie | **[A CONFIRMER]** |

Ces trois lignes ne sont pas resolues. Elles ne bloquent pas la lecture de ce
document, elles bloquent l'assemblage.

## 6. Regle d'ordre de montage

> **Attribuer les ID servo AVANT l'assemblage mecanique.**
>
> Un servo monte dans le bras n'est plus accessible seul sur le bus. Changer un
> ID apres coup signifie demonter. Les 6 servos d'un bras doivent porter les ID
> 1 a 6 et etre configures un par un, bus vide, avant d'entrer dans une piece.

## 7. Calcul materiel pour une seconde paire

12 servos (7 C001 / 2 C044 / 3 C046), 2 cartes Waveshare, 2 blocs 5 V / 4 A,
2 cables USB-C data, 2 jeux PRINT_SET_001, 2 cameras.

> Un cable USB-C de **charge** n'a pas de lignes de donnees. Il alimente et
> n'etablit aucun port serie. C'est la premiere chose a eliminer quand
> `scripts/find_ports.sh` ne voit rien.
