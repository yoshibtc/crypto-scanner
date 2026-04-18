-- Operational views (run manually: psql $DATABASE_URL -f cgd/db/views.sql)

CREATE OR REPLACE VIEW v_gaps_by_pattern AS
SELECT pattern_id, status, COUNT(*) AS n
FROM gaps
GROUP BY pattern_id, status
ORDER BY pattern_id, status;

CREATE OR REPLACE VIEW v_gap_events_recent AS
SELECT id, gap_id, event_type, reason_codes, meta, created_at
FROM gap_events
ORDER BY created_at DESC
LIMIT 2000;

CREATE OR REPLACE VIEW v_source_health AS
SELECT source_key, venue_id, degraded, fail_streak, success_streak, last_ok_at, updated_at
FROM source_health
ORDER BY degraded DESC, fail_streak DESC;

CREATE OR REPLACE VIEW v_evaluation_runs_recent AS
SELECT id, entity_id, semantics_version, matrix_version, as_of, inputs_hash, shadow_mode, created_at
FROM evaluation_runs
ORDER BY created_at DESC
LIMIT 500;

CREATE OR REPLACE VIEW v_gap_outcomes AS
SELECT o.id, o.gap_id, o.actionable, o.still_true_7d, o.labeled_at, g.pattern_id, g.entity_id,
  o.ret_1h_pct, o.ret_4h_pct, o.ret_24h_pct, o.ret_7d_pct, o.computed_at
FROM gap_outcomes o
JOIN gaps g ON g.id = o.gap_id
ORDER BY o.labeled_at DESC;

CREATE OR REPLACE VIEW v_gap_forward_returns AS
SELECT g.id AS gap_id, g.pattern_id, g.entity_id, g.opened_at, g.status,
  o.ret_1h_pct, o.ret_4h_pct, o.ret_24h_pct, o.ret_7d_pct, o.computed_at
FROM gaps g
LEFT JOIN gap_outcomes o ON o.gap_id = g.id;

CREATE OR REPLACE VIEW v_gap_outcomes_by_pattern AS
SELECT g.pattern_id,
  COUNT(*) AS n,
  AVG(o.ret_24h_pct) AS avg_ret_24h,
  AVG(o.ret_1h_pct) AS avg_ret_1h
FROM gaps g
JOIN gap_outcomes o ON o.gap_id = g.id
WHERE o.ret_24h_pct IS NOT NULL
GROUP BY g.pattern_id;

CREATE OR REPLACE VIEW v_gap_precision_by_regime AS
SELECT g.pattern_id,
       mf.payload->>'trend' AS regime_trend,
       mf.payload->>'realized_vol_bucket' AS regime_vol,
       COUNT(*) AS n,
       AVG(o.ret_24h_pct) AS avg_ret_24h
FROM gaps g
JOIN gap_outcomes o ON o.gap_id = g.id
LEFT JOIN LATERAL (
  SELECT mf2.payload
  FROM market_facts mf2
  WHERE mf2.fact_type = 'btc_regime'
    AND mf2.entity_id IS NULL
    AND mf2.source_ts <= g.opened_at
  ORDER BY mf2.source_ts DESC
  LIMIT 1
) mf ON true
WHERE o.ret_24h_pct IS NOT NULL
GROUP BY g.pattern_id, mf.payload->>'trend', mf.payload->>'realized_vol_bucket';
