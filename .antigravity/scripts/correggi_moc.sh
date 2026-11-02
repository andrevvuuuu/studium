#!/bin/bash
# ==============================================================================
# .antigravity/scripts/correggi_moc.sh
#
# Verifica e corregge (via agy, quota di Antigravity) tutte le note collegate a un MOC (correctness_check.py --fix).
# Uso:  correggi_moc.sh "Analisi 1 MOC"          solo note mai verificate o con errori rimasti
#       correggi_moc.sh "Analisi 1 MOC" --tutte  anche quelle già verificate
# Circa 4 minuti a nota, 3 note alla volta (ANTIGRAVITY_VERIFY_PARALLEL per cambiarlo); backup in .antigravity/backups/.
# ==============================================================================

set -e
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

VAULT_DIR="${ANTIGRAVITY_VAULT_DIR:-$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../.." && pwd)}"
NAME="${1%.md}"
if [ -z "$NAME" ]; then
    echo "Uso: $0 \"Nome del MOC\" [--tutte]"
    exit 1
fi

MOC=$(find "$VAULT_DIR" -path "$VAULT_DIR/.*" -prune -o -type f -name "$NAME.md" -print | head -n 1)
if [ -z "$MOC" ]; then
    echo "MOC non trovato: $NAME.md"
    exit 1
fi

FILTER=(--skip-verified --recheck)
[ "$2" = "--tutte" ] && FILTER=()

echo "Verifica e correzione delle note collegate a: ${MOC#$VAULT_DIR/}"
cd "$VAULT_DIR"
python3 "$VAULT_DIR/.antigravity/tools/correctness_check.py" --moc "$MOC" --fix --parallel "${ANTIGRAVITY_VERIFY_PARALLEL:-3}" "${FILTER[@]}"
