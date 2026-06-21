# DeepSeek Gateway Recovery Guide

## Restore Database
1. cd /opt/deepseek-gateway
2. docker compose down
3. cp backups/db.sqlite3.backup.DATE data/db.sqlite3
4. docker compose up -d --build

## Tests
- Health: curl -s http://127.0.0.1/health
- Usage: docker compose exec deepseek-gateway python usage_report.py
- Restart: docker compose down && docker compose up -d --build