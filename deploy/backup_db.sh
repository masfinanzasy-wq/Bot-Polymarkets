#!/bin/bash
# Script de Backup automatizado de PostgreSQL para el Bot de Polymarket
set -e

BACKUP_DIR="/var/backups/polymarket-bot"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/postgres_backup_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Iniciando copia de seguridad de PostgreSQL..."
docker exec polymarket_postgres pg_dump -U bot_user -d polymarket_db | gzip > "${BACKUP_FILE}"

echo "[$(date)] Copia de seguridad guardada exitosamente en ${BACKUP_FILE}"

# Retener solo los ultimos 7 dias de copias
find "${BACKUP_DIR}" -type f -name "postgres_backup_*.sql.gz" -mtime +7 -delete
echo "[$(date)] Limpieza de backups antiguos completada."
