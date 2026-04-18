-- Optional retention for Timescale hypertable market_facts (run once in psql).
-- Safe to run multiple times only if policy not already added (Timescale returns error).
SELECT add_retention_policy('market_facts', INTERVAL '90 days');
