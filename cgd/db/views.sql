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
SELECT o.id, o.gap_id, o.actionable, o.still_true_7d, o.labeled_at, g.pattern_id, g.entity_id
FROM gap_outcomes o
JOIN gaps g ON g.id = o.gap_id
ORDER BY o.labeled_at DESC;
