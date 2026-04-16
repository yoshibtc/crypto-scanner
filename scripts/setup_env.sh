#!/usr/bin/env bash
# Usage: bash scripts/setup_env.sh YOUR_BOT_TOKEN
# Example: bash scripts/setup_env.sh 123456:ABC-xyz
set -euo pipefail
TOKEN="${1:?Pass your Telegram bot token as first argument}"
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cat > "$APP_DIR/.env" <<EOF
DATABASE_URL=postgresql+psycopg2://cgd:cgd_dev_change_me@127.0.0.1:5432/cgd
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
TELEGRAM_BOT_TOKEN=$TOKEN
TELEGRAM_CHAT_ID=576662320
SHADOW_MODE=0
EOF

chmod 600 "$APP_DIR/.env"
echo ".env written."

source "$APP_DIR/.venv/bin/activate"
python3 "$APP_DIR/scripts/test_telegram.py"

systemctl restart celery-worker celery-beat 2>/dev/null && echo "Workers restarted." || echo "systemctl not available, skip restart."
