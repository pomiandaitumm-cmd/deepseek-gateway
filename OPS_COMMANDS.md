# Ops Commands Quick Reference

## Key Management

Create: docker compose exec deepseek-gateway python create_key.py --name "username" --token-quota 100000
Disable: docker compose exec deepseek-gateway python disable_key.py --prefix sk-gateway-xxxx
Add Quota: docker compose exec deepseek-gateway python add_quota.py --prefix sk-gateway-xxxx --tokens 50000
Set Quota: docker compose exec deepseek-gateway python set_quota.py --prefix sk-gateway-xxxx --tokens 100000
View Usage: docker compose exec deepseek-gateway python usage_report.py

## Docker

Status: docker compose ps
Logs: docker compose logs --tail 50
Restart: docker compose down && docker compose up -d --build

## System

Nginx: systemctl status nginx
fail2ban: fail2ban-client status sshd
Firewall: firewall-cmd --list-all

## Backups

Database: cp data/db.sqlite3 backups/db.sqlite3.backup.
Project: cd /opt && tar --exclude=deepseek-gateway/backups -czf deepseek-gateway/backups/deepseek-gateway-alpha-backup-.tar.gz deepseek-gateway