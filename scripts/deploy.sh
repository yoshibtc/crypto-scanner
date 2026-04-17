#!/usr/bin/env bash
# One-command deploy on the Droplet. Run after every git push:
#   bash /root/crypto-scanner/scripts/deploy.sh
#
# Pulls latest code, reinstalls the package, runs migrations, restarts services.
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$APP_DIR/.venv"

cd "$APP_DIR"

echo "==> [1/4] git pull"
git pull --ff-only

echo "==> [2/4] pip install -e ."
"$VENV/bin/pip" install -q -e "$APP_DIR"

echo "==> [3/4] alembic upgrade head"
"$VENV/bin/alembic" -c "$APP_DIR/alembic.ini" upgrade head

echo "==> [4/4] Restart services"
# Restart only services that are installed; ignore missing ones.
for svc in celery-worker celery-beat cgd-bot; do
  if systemctl list-unit-files | grep -q "^${svc}.service"; then
    systemctl restart "$svc" && echo "  restarted $svc"
  else
    echo "  skipped $svc (not installed)"
  fi
done

echo ""
echo "Deploy complete."
