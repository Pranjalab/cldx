#!/usr/bin/env bash
# cldx uninstaller — removes the cldx package and (optionally) ~/.cldx state.
#
#   ./uninstall.sh           # uninstall, prompt before wiping ~/.cldx
#   ./uninstall.sh --purge   # uninstall and wipe ~/.cldx with no prompt
#   ./uninstall.sh --keep    # uninstall and leave ~/.cldx untouched

set -euo pipefail

CLDX_HOME="${CLDX_HOME:-$HOME/.cldx}"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=11

# --- ANSI helpers ---------------------------------------------------------
if [ -t 1 ]; then
  C_OK=$'\e[32m'; C_WARN=$'\e[33m'; C_ERR=$'\e[31m'; C_BOLD=$'\e[1m'; C_RST=$'\e[0m'
else
  C_OK=''; C_WARN=''; C_ERR=''; C_BOLD=''; C_RST=''
fi
say()  { printf '%s%s%s\n' "$C_OK"  "✓ $1" "$C_RST"; }
warn() { printf '%s%s%s\n' "$C_WARN" "! $1" "$C_RST"; }
die()  { printf '%s%s%s\n' "$C_ERR" "✗ $1" "$C_RST" >&2; exit 1; }
head() { printf '\n%s%s%s\n' "$C_BOLD" "$1" "$C_RST"; }

# --- Pick a Python ≥ 3.11 -------------------------------------------------
pick_python() {
  for cand in python3.13 python3.12 python3.11 python3; do
    if command -v "$cand" >/dev/null 2>&1; then
      ver=$("$cand" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null || echo 0.0)
      maj=${ver%.*}; min=${ver#*.}
      if [ "$maj" -ge "$MIN_PYTHON_MAJOR" ] && [ "$min" -ge "$MIN_PYTHON_MINOR" ]; then
        echo "$cand"
        return 0
      fi
    fi
  done
  return 1
}

# --- Parse flags ----------------------------------------------------------
PURGE_MODE="prompt"   # prompt | yes | no
for arg in "$@"; do
  case "$arg" in
    --purge|-p) PURGE_MODE="yes" ;;
    --keep|-k)  PURGE_MODE="no" ;;
    --help|-h)
      cat <<EOF
Usage: ./uninstall.sh [--purge | --keep]

  --purge, -p   Remove the cldx package and wipe ${CLDX_HOME} without asking.
  --keep,  -k   Remove the cldx package but keep ${CLDX_HOME} intact.
  (no flag)     Remove the package and ask before wiping ${CLDX_HOME}.
EOF
      exit 0
      ;;
    *) die "unknown flag: $arg (try --help)" ;;
  esac
done

head "cldx uninstaller"

PY=$(pick_python) || die "no compatible Python ≥${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR} on PATH"
PY_VER=$("$PY" --version 2>&1)
say "Using $PY ($PY_VER)"

# --- 1. Uninstall the package via pip -------------------------------------
head "Removing cldx package"
if "$PY" -m pip show cldx >/dev/null 2>&1; then
  if "$PY" -m pip uninstall --yes --break-system-packages cldx >/dev/null 2>&1 \
     || "$PY" -m pip uninstall --yes cldx >/dev/null 2>&1; then
    say "Uninstalled cldx via pip"
  else
    die "pip uninstall failed. Try \`$PY -m pip uninstall cldx\` manually."
  fi
else
  warn "cldx is not installed under $PY — nothing to remove from pip"
fi

# --- 2. Decide what to do about ~/.cldx -----------------------------------
head "User state at ${CLDX_HOME}"
if [ ! -d "$CLDX_HOME" ]; then
  say "No state directory found — nothing to clean up"
  head "Done."
  exit 0
fi

case "$PURGE_MODE" in
  yes)
    rm -rf "$CLDX_HOME"
    say "Removed ${CLDX_HOME}"
    ;;
  no)
    warn "Left ${CLDX_HOME} in place (re-install will reuse your config)"
    ;;
  prompt)
    echo "    ${CLDX_HOME} contains your config, session logs, and learned policy."
    printf "    Delete it? [y/N] "
    read -r ans </dev/tty || ans=""
    case "$ans" in
      y|Y|yes|YES)
        rm -rf "$CLDX_HOME"
        say "Removed ${CLDX_HOME}"
        ;;
      *)
        warn "Left ${CLDX_HOME} in place (re-install will reuse your config)"
        ;;
    esac
    ;;
esac

head "Done."
echo "    Re-install any time with: ./install.sh"
