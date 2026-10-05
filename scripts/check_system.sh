#!/usr/bin/env bash
# check_system.sh — inventaire LECTURE SEULE de l'environnement.
# N'installe rien. N'ouvre aucun port. Ne fait bouger aucun moteur.
set -uo pipefail

echo "=== SYSTEME ==="
UNAME=$(uname -s)
printf "  OS            : %s %s\n" "$UNAME" "$(uname -r)"
if [ "$UNAME" = "Darwin" ]; then
  printf "  version macOS : %s\n" "$(sw_vers -productVersion 2>/dev/null || echo inconnue)"
elif [ -f /etc/os-release ]; then
  printf "  distribution  : %s\n" "$(. /etc/os-release; echo "$PRETTY_NAME")"
fi
printf "  architecture  : %s\n" "$(uname -m)"
if [ "$UNAME" = "Darwin" ]; then
  printf "  CPU           : %s\n" "$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo inconnu)"
elif [ -f /proc/cpuinfo ]; then
  printf "  CPU           : %s\n" "$(grep -m1 -E 'model name|Model' /proc/cpuinfo | cut -d: -f2- | sed 's/^ *//')"
fi

echo
echo "=== PYTHON ==="
if command -v python3 >/dev/null 2>&1; then
  printf "  python3       : %s\n" "$(python3 --version 2>&1)"
  printf "  chemin        : %s\n" "$(command -v python3)"
else
  echo "  python3       : ABSENT"
fi
for t in uv pip3 conda poetry; do
  printf "  %-13s : %s\n" "$t" "$(command -v $t 2>/dev/null || echo absent)"
done
[ -n "${VIRTUAL_ENV:-}" ] && printf "  venv actif    : %s\n" "$VIRTUAL_ENV" || echo "  venv actif    : aucun"

echo
echo "=== LEROBOT ==="
if command -v python3 >/dev/null 2>&1 && python3 -c "import lerobot" >/dev/null 2>&1; then
  printf "  present       : OUI\n"
  LR_VERSION=$(python3 -c 'import lerobot;print(getattr(lerobot,"__version__","inconnue"))' 2>/dev/null)
  printf "  version       : %s\n" "$LR_VERSION"
  if [ "$LR_VERSION" = "unknown" ] || [ "$LR_VERSION" = "inconnue" ] || [ -z "$LR_VERSION" ]; then
    echo "  attendu       : 0.6.1 (decision HQ) — version indeterminee dans cet environnement"
  elif [ "$LR_VERSION" = "0.6.1" ]; then
    echo "  attendu       : 0.6.1 — conforme a la decision HQ, NON validee pour autant"
  else
    echo "  attendu       : 0.6.1 (decision HQ) — ECART : cet environnement n'est pas sur la version retenue"
  fi
  printf "  chemin        : %s\n" "$(python3 -c 'import lerobot,os;print(os.path.dirname(lerobot.__file__))' 2>/dev/null)"
  echo "  --- support SO-101 (modules generiques so_follower / so_leader) ---"
  python3 - <<'PY' 2>/dev/null
import lerobot, os
b = os.path.dirname(lerobot.__file__)
for d in ("robots", "teleoperators"):
    p = os.path.join(b, d)
    if os.path.isdir(p):
        hits = [x for x in os.listdir(p) if x.startswith("so_") or x.startswith("bi_so")]
        print(f"      {d}/ : {', '.join(sorted(hits)) if hits else 'aucun module so_*'}")
PY
else
  echo "  present       : NON"
  echo "  note          : version retenue 0.6.1 (decision HQ), pas encore installee."
  echo "                  Voir setup/mac.md — LEROBOT_VERSION_STATUS = PLANNED"
fi

echo
echo "=== PERIPHERIQUES USB (lecture seule) ==="
if [ "$UNAME" = "Darwin" ]; then
  # ioreg et non system_profiler : SPUSBDataType rend une sortie vide sur
  # macOS 26 (verifie le 2026-10-05).
  OUT=$(ioreg -p IOUSB -w0 -l 2>/dev/null \
        | grep -E '"USB Product Name"' \
        | sed -E 's/.*= "(.*)"/      \1/')
  [ -n "$OUT" ] && echo "$OUT" || echo "      aucun peripherique USB rapporte par le systeme"
else
  command -v lsusb >/dev/null 2>&1 && lsusb | sed 's/^/      /' || echo "      lsusb absent"
fi

echo
echo "Termine. Aucun port ouvert, aucune commande envoyee, aucun moteur sollicite."
