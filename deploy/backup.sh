#!/usr/bin/env bash
# Backup diario de Morfi Center: copia la base SQLite y los comprobantes de
# pago a ~/backups/<timestamp>/, y retiene solo los últimos 14 backups
# (14 días) para no llenar el disco. Sin dependencias externas.
set -euo pipefail

APP_DIR="$HOME/morfi_center/backend"
BACKUP_DIR="$HOME/backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DEST="$BACKUP_DIR/$TIMESTAMP"

mkdir -p "$DEST"

if [ -f "$APP_DIR/data/morfi.db" ]; then
  cp "$APP_DIR/data/morfi.db" "$DEST/morfi.db"
fi

if [ -d "$APP_DIR/storage/payment_proofs" ]; then
  cp -r "$APP_DIR/storage/payment_proofs" "$DEST/payment_proofs"
fi

# Retención: solo los últimos 14 backups.
cd "$BACKUP_DIR"
ls -1t | tail -n +15 | xargs -r rm -rf

echo "[$(date -Iseconds)] Backup completado: $DEST"
