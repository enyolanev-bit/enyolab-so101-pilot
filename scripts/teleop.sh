#!/usr/bin/env bash
# teleop.sh — VOLONTAIREMENT BLOQUE.
#
# Ce script NE PILOTE PAS le robot et ne doit pas etre "repare" pour
# faire avancer une tache. Son blocage est l'etat correct du systeme.
set -uo pipefail

echo "BLOCKED: teleoperation has not been validated yet" >&2
echo >&2
echo "Raisons, au 2026-10-05 (audit ENYO-14) :" >&2
echo "  - calibration leader : NOT_FOUND" >&2
echo "  - teleoperation physique : NOT_PROVEN" >&2
echo "  - validite physique de la calibration follower : TO_REVALIDATE" >&2
echo "  - version LeRobot du projet : 0.6.1 installee sur le Mac ENYOLAB (logiciel" >&2
echo "    seulement), NON installee sur le Mac de Boris, aucune validation materielle" >&2
echo >&2
echo "Conditions de deblocage, toutes requises :" >&2
echo "  1. bras leader mecaniquement complet (voir ENYO-6) ;" >&2
echo "  2. calibration leader obtenue et conservee, presente sur l'hote de" >&2
echo "     deploiement (Pilote #001 : Mac de Boris) ;" >&2
echo "  3. calibration follower revalidee sur le robot assemble, presente sur" >&2
echo "     l'hote de deploiement ;" >&2
echo "  4. version LeRobot explicitement epinglee et validee sur la cible de" >&2
echo "     deploiement utilisee pour CETTE session (Pilote #001 : Mac de Boris ;" >&2
echo "     Jetson et Raspberry Pi ne sont pas requis pour le Mac direct)." >&2
echo "     Le .venv du Mac ENYOLAB (bring-up) ne remplit PAS cette condition ;" >&2
echo "     une teleop de bring-up sur le Mac ENYOLAB exige sa propre decision HQ" >&2
echo "     documentee ;" >&2
echo "  4b. conformite physique du leader a l'affectation amont (docs/hardware.md)" >&2
echo "      relevee et consignee dans evidence/ (actuellement non relevee) ;" >&2
echo "  5. docs/safety.md lu, zone degagee, coupure d'alimentation a portee ;" >&2
echo "  6. autorisation humaine explicite pour CETTE session." >&2
echo >&2
echo "Le deblocage est une decision humaine documentee, pas une modification" >&2
echo "de ce fichier par un agent. Voir AGENTS.md." >&2
exit 1
