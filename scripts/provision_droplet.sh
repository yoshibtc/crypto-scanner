#!/usr/bin/env bash
# Run ONCE on the Droplet as root:
#   bash /root/crypto-scanner/scripts/provision_droplet.sh
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$APP_DIR/.venv"
DB_URL="${DATABASE_URL:-postgresql+psycopg2://cgd:cgd_dev_change_me@127.0.0.1:5432/cgd}"

echo "==> [1/7] System packages"
apt-get update -qq
apt-get install -y -qq python3-venv python3-pip curl git

echo "==> [2/7] Docker"
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
docker --version
docker compose version

echo "==> [3/7] Start Postgres + Redis"
cd "$APP_DIR"
docker compose up -d
echo "Waiting for Postgres..."
for _ in $(seq 1 60); do
  docker compose exec -T postgres pg_isready -U cgd -d cgd &>/dev/null && break || sleep 2
done
docker compose exec -T postgres pg_isready -U cgd -d cgd || { echo "Postgres not ready"; exit 1; }

echo "==> [4/7] Python venv + pip install"
python3 -m venv "$VENV"
"$VENV/bin/pip" install -q -U pip
"$VENV/bin/pip" install -q -e "$APP_DIR/.[dev]"

echo "==> [5/7] Migrations + seed"
DATABASE_URL="$DB_URL" "$VENV/bin/alembic" -c "$APP_DIR/alembic.ini" upgrade head
DATABASE_URL="$DB_URL" "$VENV/bin/python" "$APP_DIR/scripts/seed_entities.py"

echo "==> [6/7] Systemd: celery-worker"
cat > /etc/systemd/system/celery-worker.service <<EOF
[Unit]
Description=Crypto Scanner Celery Worker
After=network.target docker.service
Requires=docker.service

[Service]
WorkingDirectory=$APP_DIR
Environment="DATABASE_URL=$DB_URL"
Environment="PATH=$VENV/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStartPre=/usr/bin/docker compose -f $APP_DIR/docker-compose.yml up -d
ExecStart=$VENV/bin/python -m celery -A cgd.workers.celery_app worker -l INFO -Q ingest_rest,ingest_ccxt,ingest_rpc,evaluate,alerts,default
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "==> [7/7] Systemd: celery-beat"
cat > /etc/systemd/system/celery-beat.service <<EOF
[Unit]
Description=Crypto Scanner Celery Beat
After=celery-worker.service
Requires=celery-worker.service

[Service]
WorkingDirectory=$APP_DIR
Environment="DATABASE_URL=$DB_URL"
Environment="PATH=$VENV/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$VENV/bin/python -m celery -A cgd.workers.celery_app beat -l INFO
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now celery-worker celery-beat

echo ""
echo "============================================"
echo "  ALL DONE. App is running."
echo "  Check status:  systemctl status celery-worker celery-beat"
echo "  Watch logs:    journalctl -u celery-worker -f"
echo "============================================"
