#!/bin/bash

# Backup-Script für die Produktionsumgebung auf Hetzner (91.99.73.203)
# Dieses Script erstellt verschlüsselte Backups aller wichtigen Daten

# Konfiguration
BACKUP_DIR="/opt/mailmind/backups"
DATE=$(date +%Y%m%d_%H%M%S)
ENCRYPTION_KEY=${BACKUP_ENCRYPTION_KEY}

# Backup-Verzeichnisse erstellen
mkdir -p "${BACKUP_DIR}/postgres"
mkdir -p "${BACKUP_DIR}/redis"
mkdir -p "${BACKUP_DIR}/qdrant"
mkdir -p "${BACKUP_DIR}/media"

# PostgreSQL Backup
echo "Backing up PostgreSQL database..."
docker exec mailmind_postgres pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} | \
  gpg --symmetric --batch --passphrase "${ENCRYPTION_KEY}" \
  > "${BACKUP_DIR}/postgres/mailmind_${DATE}.sql.gpg"

# Redis Backup
echo "Backing up Redis data..."
docker exec mailmind_redis redis-cli -a "${REDIS_PASSWORD}" SAVE
docker cp mailmind_redis:/data/dump.rdb "${BACKUP_DIR}/redis/dump_${DATE}.rdb"
gpg --symmetric --batch --passphrase "${ENCRYPTION_KEY}" \
  "${BACKUP_DIR}/redis/dump_${DATE}.rdb"
rm "${BACKUP_DIR}/redis/dump_${DATE}.rdb"

# Qdrant Backup
echo "Backing up Qdrant data..."
tar -czf - /opt/mailmind/volumes/qdrant_data | \
  gpg --symmetric --batch --passphrase "${ENCRYPTION_KEY}" \
  > "${BACKUP_DIR}/qdrant/qdrant_${DATE}.tar.gz.gpg"

# Media Files Backup
echo "Backing up media files..."
tar -czf - /opt/mailmind/backend/media | \
  gpg --symmetric --batch --passphrase "${ENCRYPTION_KEY}" \
  > "${BACKUP_DIR}/media/media_${DATE}.tar.gz.gpg"

# Alte Backups aufräumen (behalte nur die letzten 7 Tage)
find "${BACKUP_DIR}" -type f -name "*.gpg" -mtime +7 -delete

# Backup auf externen Storage kopieren (optional)
if [ -n "${REMOTE_BACKUP_URL}" ]; then
  echo "Copying backups to remote storage..."
  rclone sync "${BACKUP_DIR}" "${REMOTE_BACKUP_URL}/mailmind_backups"
fi

echo "Backup completed successfully!" 