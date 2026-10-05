# Materiel

Etat au **2026-10-05**. Chaque ligne porte son niveau de preuve.

## 1. Bras

| Element | Valeur | Preuve |
|---|---|---|
| Modele | SO-101, variante **Standard** | PROVEN — decision HQ, archi arretee |
| Bras | 1 leader + 1 follower | PROVEN |
| Servos par bras | 6 | PROVEN |
| Tension servos | **7.4 V** pour les deux bras | PROVEN — doc upstream SO-ARM100 |
| Variante Pro / follower 12 V | **non utilisee** | PROVEN — decision HQ |

### Repartition des servos (par bras, 6 unites)

| Reference | Reduction | Qte / bras |
|---|---|---|
| Feetech STS3215 **C001** | 1:345 | 7 sur les 12 |
| Feetech STS3215 **C044** | 1:191 | 2 sur les 12 |
| Feetech STS3215 **C046** | 1:147 | 3 sur les 12 |

Total 12 pour la paire — repartition 7 / 2 / 3 issue de la nomenclature upstream.

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
| Alimentation cible | **5 V / 4 A minimum**, un bloc par bras | PROVEN — decision HQ |
| Modele retenu | Mean Well **GST25E05-P1J** | PROVEN |
| Polarite | **centre positif** — suffixe `P1J` = 2.1 x 5.5 x 11 mm, C+ | PROVEN — datasheet constructeur |

> ⚠️ **Divergence a connaitre.** La datasheet Waveshare annonce une plage
> d'entree **9–12.6 V**, alors que l'architecture retenue est **5 V**. Les deux
> informations sont exactes et elles ne concordent pas. Ce point est
> **[A VERIFIER AVANT MISE SOUS TENSION]** : relire la datasheet de la carte
> reellement en main et confirmer que 5 V est dans sa plage admissible.
> Ne pas alimenter en se fiant a ce document.

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
- 2 vues sont necessaires a l'entrainement. Une seule ne suffit pas.
- La webcam du portable n'est **pas** une des deux vues.

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
