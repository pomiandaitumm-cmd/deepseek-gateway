#!/bin/bash
# ==============================================
# DeepSeek API Gateway - VPS Deployment Script
# Supports: AlmaLinux / Rocky / RHEL / CentOS / Fedora / Ubuntu / Debian
# ==============================================
set -euo pipefail

APP_DIR="/opt/deepseek-gateway"
DATA_DIR="$APP_DIR/data"
DB_FILE="$DATA_DIR/db.sqlite3"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

die() { echo -e "${RED}[FATAL] $1${NC}" >&2; exit 1; }

# ============================
# Step 0: Detect OS
# ============================
echo -e "${GREEN}[0/6] Detecting OS...${NC}"

if [ ! -f /etc/os-release ]; then
    die "Cannot detect OS: /etc/os-release not found"
fi

. /etc/os-release
OS_ID="${ID}"
OS_ID_LIKE="${ID_LIKE:-}"
echo "  Detected: $NAME ($ID)"

# Determine package manager
IS_RHEL=false
IS_DEBIAN=false

case "$OS_ID" in
    almalinux|rocky|rhel|centos|fedora|amzn|ol|oraclelinux)
        IS_RHEL=true ;;
    ubuntu|debian)
        IS_DEBIAN=true ;;
    *)
        # Check ID_LIKE as fallback
        if echo "$OS_ID_LIKE" | grep -qE "rhel|fedora|centos"; then
            IS_RHEL=true
        elif echo "$OS_ID_LIKE" | grep -qE "debian|ubuntu"; then
            IS_DEBIAN=true
        else
            die "Unsupported OS: $NAME ($ID). Please install Docker and Nginx manually."
        fi
        ;;
esac

echo "  Package family: $( $IS_RHEL && echo RHEL/dnf || echo Debian/apt )"

# ============================
# Step 1: Install Docker
# ============================
echo -e "${GREEN}[1/6] Installing Docker...${NC}"

if command -v docker &>/dev/null; then
    echo -e "${YELLOW}  Docker already installed: $(docker --version)${NC}"
else
    if $IS_RHEL; then
        echo "  Installing Docker CE via dnf..."
        dnf install -y dnf-plugins-core || die "Failed to install dnf-plugins-core"
        dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo || die "Failed to add Docker repo"
        dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || die "Failed to install Docker packages"
    else
        echo "  Installing Docker CE via apt..."
        apt-get update -qq || die "apt-get update failed"
        apt-get install -y -qq ca-certificates curl || die "Failed to install prerequisites"
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
        chmod a+r /etc/apt/keyrings/docker.asc
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
        apt-get update -qq || die "apt-get update after adding Docker repo failed"
        apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || die "Failed to install Docker packages"
    fi

    systemctl enable --now docker || die "Failed to start Docker"
    echo "  Docker installed successfully."
fi

# Verify docker compose plugin
if ! docker compose version &>/dev/null; then
    die "docker compose plugin not available"
fi
echo "  docker compose: $(docker compose version)"

# ============================
# Step 2: Install Nginx
# ============================
echo -e "${GREEN}[2/6] Installing Nginx...${NC}"

if command -v nginx &>/dev/null; then
    echo -e "${YELLOW}  Nginx already installed: $(nginx -v 2>&1)${NC}"
else
    if $IS_RHEL; then
        dnf install -y nginx || die "Failed to install nginx via dnf"
    else
        apt-get install -y -qq nginx || die "Failed to install nginx via apt"
    fi
    echo "  Nginx installed."
fi

systemctl enable --now nginx || die "Failed to start nginx"

# ============================
# Step 3: Firewall
# ============================
echo -e "${GREEN}[3/6] Configuring firewall...${NC}"

if command -v firewall-cmd &>/dev/null && systemctl is-active --quiet firewalld 2>/dev/null; then
    echo "  firewalld detected. Opening port 80..."
    firewall-cmd --add-service=http --permanent 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
    echo "  Port 80 opened."
elif command -v ufw &>/dev/null; then
    echo "  ufw detected. Opening port 80..."
    ufw allow 80/tcp 2>/dev/null || true
    echo "  Port 80 opened."
else
    echo "  No firewall detected or firewall not running. Skipping."
fi

# ============================
# Step 4: Prepare directories
# ============================
echo -e "${GREEN}[4/6] Preparing directories...${NC}"
mkdir -p "$DATA_DIR"

if [ -f "$DB_FILE" ]; then
    echo -e "${YELLOW}  [SKIP] db.sqlite3 exists at $DB_FILE -- will NOT overwrite${NC}"
else
    echo "  No existing database. Will be created on first container start."
fi

# ============================
# Step 5: Start container
# ============================
echo -e "${GREEN}[5/6] Building and starting container...${NC}"
cd "$APP_DIR" || die "Cannot cd to $APP_DIR"

# Graceful shutdown if running
docker compose down --remove-orphans 2>/dev/null || true
docker compose up -d --build || die "docker compose up failed"

echo "  Container started. Waiting for healthy..."
for i in $(seq 1 15); do
    if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
        echo "  Container healthy."
        break
    fi
    sleep 2
done

# ============================
# Step 6: Nginx reverse proxy
# ============================
echo -e "${GREEN}[6/6] Configuring Nginx reverse proxy...${NC}"

if $IS_RHEL; then
    NGINX_CONF="/etc/nginx/conf.d/deepseek-gateway.conf"
    # Remove default server block if present
    rm -f /etc/nginx/conf.d/default.conf 2>/dev/null || true
else
    NGINX_CONF="/etc/nginx/sites-available/deepseek-gateway"
fi

cat > "$NGINX_CONF" << 'NGINX'
server {
    listen 80;
    server_name _;

    client_max_body_size 10m;

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;

        # SSE streaming support
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;
    }
}
NGINX

if ! $IS_RHEL; then
    ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
fi

nginx -t || die "Nginx configuration test failed"
systemctl reload nginx || die "Failed to reload nginx"

# ============================
# Done
# ============================
echo ""
echo -e "${GREEN}======================================"
echo "  DeepSeek Gateway Deployed!"
echo "======================================${NC}"
echo ""
echo "  Health:   curl http://<vps-ip>/health"
echo "  Models:   curl http://<vps-ip>/v1/models -H 'Authorization: Bearer <key>'"
echo ""
echo "  Logs:     docker logs deepseek-gateway -f"
echo "  Restart:  cd $APP_DIR && docker compose restart"
echo "  New key:  docker exec deepseek-gateway python create_key.py --name user-x"
echo "  Report:   docker exec deepseek-gateway python usage_report.py"
echo "  Database: $DB_FILE (persisted on host, safe from overwrites)"
echo ""
