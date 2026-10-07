# Démonstration de bout en bout du 2026-10-07 11:34 : papier vierge — diagnostic

## Constat (opérateur)

| Point | Statut |
|---|---|
| Commande Astra valide | **OUI** : `golden_gate_bridge`, échelle 1,0, `resp_01a79ff8…`, 838 tokens |
| Trajectoire du robot exécutée | **OUI** : 78/78 points de passage, 73 s, couple relu à 0 ×6 |
| Marque physique produite | **NON** : papier entièrement vierge |
| Dessin de bout en bout réussi | **NON** |

## Analyse des preuves (images avant et après, journaux moteur ; aucune image prise pendant le tracé)

1. **Pointe en contact avant le mouvement : NON VÉRIFIABLE.**
   - La caméra outil vise le long du marqueur : perspective trop ambiguë pour juger le contact. La pointe apparaît **au bord de la feuille, sur la bande plastique transparente** qui la maintient.
   - La caméra de contexte ne voit pas la zone de la pointe : la feuille qu'elle montre est vierge même après le pont n° 3, pourtant confirmé.
2. **Contact maintenu pendant le tracé : INCONNU.** Pas d'image prise pendant le tracé.
   - Le signal de frottement dans les journaux (consigne − mesure ≈ 9 pas) est **identique** pour le pont n° 3 (dessiné) et pour cet essai (vierge). C'est l'erreur statique du servo dans cette pose : le journal moteur **ne prouve pas** le contact.
3. **La trajectoire éloigne-t-elle la pointe du papier ?**
   - **Pour le tablier, non par construction** : c'est `shoulder_pan` seul, une rotation autour d'un axe vertical, qui conserve la hauteur de la pointe.
   - Un tablier vierge implique donc **l'absence de contact avec le papier dès le départ**, ou une pointe posée hors du papier (bande plastique).
   - `wrist_flex` peut soulever ou appuyer la pointe si le marqueur n'est pas perpendiculaire à la feuille. La FK, non vérifiée, donne un outil proche de l'horizontale : **risque possible** pour les tours, sans effet sur le tablier.
4. **Hypothèse de plan de dessin :** la feuille est horizontale sur la table (images). Le pan reste dans le plan. La validité de l'axe v (`wrist_flex`) dépend de l'inclinaison du marqueur : **ASSUMED**.
5. **Le robot a-t-il bougé ?** Oui, d'après les encodeurs (positions mesurées en sortie de servo) : pan +8,0° et retour, wrist ±3,2°. Mouvement visuel non observé par l'agent.
   - La pose de départ est **identique à 2 pas près à celle du pont n° 3** : le bras n'a pas été déplacé entre les deux essais. Seul le papier a changé (vierge), ce qui confirme l'hypothèse d'une absence de contact.

## Cause la plus probable (ASSUMED, la plus forte compatible avec les faits)

**La pointe ne touchait pas la feuille au départ** : marqueur au-dessus de la nouvelle feuille, ou posé sur la bande plastique. Le logiciel et la trajectoire ne sont pas en cause pour le tablier.

## Correctifs

- Physique : pointe posée **sur la feuille, loin de la bande plastique**, contact vérifié par une petite marque à la main ; caméra de contexte orientée sur la pointe si possible.
- Logiciel : `run_boris.py` capture désormais une **image de la caméra de contexte pendant le tracé** et demande une **confirmation explicite du contact** avant GO.
- Ordre convenu : d'abord une marque locale déterministe (pan +3°), puis le plus petit dessin viable, puis Astra.
