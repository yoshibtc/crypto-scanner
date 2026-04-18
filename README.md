# Crypto Gap Detector (CGD)

Deterministic Tier 1 baseline: PostgreSQL with TimescaleDB ([`timescale/timescaledb:latest-pg16`](https://hub.docker.com/r/timescale/timescaledb) in Docker), Celery + Redis, DeFiLlama + CCXT collectors, gap lifecycle, optional Telegram alerts.

## Quick start

1. Copy `.env.example` to `.env` and adjust `DATABASE_URL`, Redis URLs, optional `TELEGRAM_*`, optional `RPC_URLS_ETHEREUM` (comma-separated failover RPCs).

2. Start infra:

```bash
docker compose up -d
```

3. Install Python 3.10+ and dependencies:

```bash
pip install -e ".[dev]"
```

4. Run migrations:

```bash
set DATABASE_URL=postgresql+psycopg2://cgd:cgd_dev_change_me@127.0.0.1:5432/cgd
alembic upgrade head
```

5. Seed pilot entities:

```bash
python scripts/seed_entities.py
```

6. Run workers (separate terminals). On Windows, if `celery` is not on `PATH`, use `python -m celery`:

```bash
python -m celery -A cgd.workers.celery_app worker -l INFO -Q ingest_rest,ingest_ccxt,ingest_rpc,evaluate,alerts,default
python -m celery -A cgd.workers.celery_app beat -l INFO
```

7. Optional SQL views (reason-code stats):

```bash
psql "$DATABASE_URL" -f cgd/db/views.sql
```

## One-shot (no Celery)

```bash
python -c "from cgd.workers.one_shot import run_evaluate; run_evaluate()"
```

## Notes

- `SHADOW_MODE=1` (default): gaps stay **DETECTED**; set `SHADOW_MODE=0` in `.env` on the Droplet (or locally) to allow **ESCALATED** + Telegram dispatch.
- Celery beat runs **fast** evaluation every 2m (`P7` + `P10` CEX) and **slow** every 20m (`P6` + `P10` DEX), plus lifecycle, labels, BTC regime, RPC health—see [cgd/workers/celery_app.py](cgd/workers/celery_app.py).
- Pattern thresholds / regime allowlists: [config/patterns.yaml](config/patterns.yaml).
- CCXT matrix: [config/ccxt_matrix.yaml](config/ccxt_matrix.yaml). Task `verify_ccxt_matrix` probes exchanges and updates **`source_health`** for each `ccxt:{id}` (same keys as ingest).
- Pattern 7 framing: **positioning / leverage stress** (see payload `framing` field).
- Timescale: `market_facts` is a hypertable on `source_ts`. Retention (run once): [cgd/db/timescale_policies.sql](cgd/db/timescale_policies.sql).
- Expand watchlist from Binance volumes: `python scripts/build_watchlist.py --top 50`

## Caveats (read once)

- **P10 seed pair** (`USDT/USDC`): a **cross-stable liquidity** proxy, not a clean USDT/USD peg; interpret CEX leg accordingly.
- **DeFiLlama JSON** varies by protocol; [`extract_protocol_snapshot`](cgd/collectors/defillama.py) flattens common shapes—expect to extend `metrics` / fee paths as you see real payloads.
- **P7 / P10 CEX gating**: both use **`any_enabled_ccxt_venue_degraded()`**—only venues with `enabled: true` in the matrix (duplicate `ccxt_id` entries in YAML are deduped). Stale `ccxt:*` rows from disabled exchanges are ignored. If **no** venue is enabled, gating is off (**fail-open**). For the stricter “any degraded `ccxt:%` row” check, see **`any_ccxt_venue_degraded()`**. **P10’s DEX** leg still runs from `onchain_facts`.
- **Migrations**: smoke-test `alembic upgrade head` against Docker Timescale once; `downgrade` uses `DROP ... CASCADE` on `market_facts` (dev-oriented).

## Tests

```bash
python -m pytest
```
