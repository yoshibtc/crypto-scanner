#!/usr/bin/env bash
# Run ONCE on the Droplet as root:
#   bash /root/crypto-scanner/scripts/install_bot_service.sh
#
# Installs a systemd service for the Telegram status bot (cgd-bot).
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$APP_DIR/.venv"

if [ ! -x "$VENV/bin/python" ]; then
  echo "Venv not found at $VENV. Run provision_droplet.sh first." >&2
  exit 1
fi

cat > /etc/systemd/system/cgd-bot.service <<EOF
[Unit]
Description=Crypto Scanner Telegram Status Bot
After=network.target celery-worker.service
Requires=celery-worker.service

[Service]
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=-$APP_DIR/.env
ExecStart=$VENV/bin/cgd-bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now cgd-bot

echo ""
echo "cgd-bot installed and started."
echo "  Status:  systemctl status cgd-bot"
echo "  Logs:    journalctl -u cgd-bot -f"
