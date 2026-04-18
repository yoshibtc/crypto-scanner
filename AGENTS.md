# Agent Guide — Crypto Gap Detector

Read this before making changes. Short by design.

## How the system runs

- **Droplet:** `root@188.166.116.73` at `/root/crypto-scanner`
- **Docker services on the Droplet:** Postgres (TimescaleDB) + Redis — bound to `127.0.0.1` only
- **Python services (systemd on the Droplet):**
  - `celery-worker.service` — runs ingest, evaluate, alert tasks
  - `celery-beat.service` — schedules those tasks
  - `cgd-bot.service` — Telegram bot (`/status`, `/watchlist`, `/watchlist_add`, `/watchlist_remove`, `/gaps`, `/resolve`, `/invalidate`, `/regime`, `/alerts`, `/health`)
- **Python venv:** `/root/crypto-scanner/.venv`
- **Secrets:** `/root/crypto-scanner/.env` (never in git; `.env.example` must stay empty for secret-like keys)

## Deploy workflow (the only way code gets to the Droplet)

**Never SSH in to copy files or edit code.** The flow is:

1. Edit code locally.
2. Commit and push to `main` on GitHub (`yoshibtc/crypto-scanner`).
3. GitHub Actions workflow `.github/workflows/deploy.yml` fires automatically:
   - SSHes to the Droplet using the `DROPLET_HOST` / `DROPLET_USER` / `DROPLET_SSH_KEY` repo secrets.
   - Runs `scripts/deploy.sh` which does: `git pull` → `pip install -e .` → `alembic upgrade head` → `systemctl restart celery-worker celery-beat cgd-bot`.
4. Watch the run at **github.com/yoshibtc/crypto-scanner/actions**.

Manual deploys (only if Actions is down): SSH in and run `bash /root/crypto-scanner/scripts/deploy.sh`.

## What NOT to commit

A pre-commit hook (`.git/hooks/pre-commit`) blocks commits if `.env.example` contains a real Telegram bot token or any filled-in `SECRET` / `PASSWORD` / `API_KEY` / `TOKEN` / `AUTH` value. Keep `.env.example` with empty values only.

## Adding a new Telegram command

1. Add a handler function in `cgd/bot/commands.py` that takes `Session` and returns `str`.
2. Wire it into the router in `cgd/bot/poller.py` (`_handle` function).
3. Add it to the `/help` text in `cmd_help()`.
4. Push → auto-deploys → works.

## Database changes

1. Edit models in `cgd/db/models.py`.
2. Create an Alembic migration: `alembic revision --autogenerate -m "description"`.
3. Commit the new file in `alembic/versions/`.
4. Push. `deploy.sh` runs `alembic upgrade head` automatically.

## Checking the Droplet when something seems off

SSH in and run:

```bash
systemctl status celery-worker celery-beat cgd-bot   # all green?
journalctl -u cgd-bot -n 50 --no-pager               # recent bot logs
journalctl -u celery-worker -n 100 --no-pager        # recent worker logs
docker compose -f /root/crypto-scanner/docker-compose.yml ps   # Postgres + Redis up?
```

## Project conventions (from user rules)

- **Keep it simple** — smallest working change.
- **Refactor before rewrite** — edit existing files, don't add new modules unless needed.
- **Reuse first** — check if the functionality already exists.
- **Explain in plain English** — short summaries, detail only when asked.
- **Why ×3** — before a change, confirm user value, business value, technical necessity.
