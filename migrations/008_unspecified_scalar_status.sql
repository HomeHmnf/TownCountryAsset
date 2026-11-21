-- Allow populated scalar observations whose provider does not publish
-- an observed/estimated/projected classification. NULL values remain restricted
-- to unavailable/not_applicable. Existing rows and identifiers are preserved.

CREATE TABLE current_statistics_v4 (
    statistic_id INTEGER PRIMARY KEY,
    game_id TEXT NOT NULL,
    statistic_key TEXT NOT NULL CHECK (length(trim(statistic_key)) > 0),
    value REAL,
    unit TEXT,
    observed_at TEXT,
    observation_period TEXT,
    value_status TEXT NOT NULL DEFAULT 'observed'
        CHECK (value_status IN ('observed', 'estimated', 'projected', 'unspecified', 'unavailable', 'not_applicable')),
    source_reference TEXT,
    source_version TEXT,
    methodology TEXT,
    retrieved_at TEXT,
    import_id INTEGER,
    UNIQUE (game_id, statistic_key),
    FOREIGN KEY (game_id) REFERENCES countries(game_id) ON DELETE RESTRICT,
    FOREIGN KEY (import_id) REFERENCES dataset_imports(import_id) ON DELETE RESTRICT,
    CHECK (
        (value IS NOT NULL AND value_status IN ('observed', 'estimated', 'projected', 'unspecified'))
        OR
        (value IS NULL AND value_status IN ('unavailable', 'not_applicable'))
    )
);

INSERT INTO current_statistics_v4 (
    statistic_id, game_id, statistic_key, value, unit, observed_at,
    observation_period, value_status, source_reference, source_version,
    methodology, retrieved_at, import_id
)
SELECT
    statistic_id, game_id, statistic_key, value, unit, observed_at,
    observation_period, value_status, source_reference, source_version,
    methodology, retrieved_at, import_id
FROM current_statistics;

DROP TABLE current_statistics;
ALTER TABLE current_statistics_v4 RENAME TO current_statistics;

CREATE INDEX ix_current_statistics_key
    ON current_statistics(statistic_key, value_status);
