-- WP1.5 statistics and selected-game-data provenance contract.
-- Rebuild current_statistics to support explicit unavailable/not-applicable values
-- and retain observation-period, source-version, retrieval and methodology metadata.

CREATE TABLE current_statistics_v3 (
    statistic_id INTEGER PRIMARY KEY,
    game_id TEXT NOT NULL,
    statistic_key TEXT NOT NULL CHECK (length(trim(statistic_key)) > 0),
    value REAL,
    unit TEXT,
    observed_at TEXT,
    observation_period TEXT,
    value_status TEXT NOT NULL DEFAULT 'observed'
        CHECK (value_status IN ('observed', 'estimated', 'projected', 'unavailable', 'not_applicable')),
    source_reference TEXT,
    source_version TEXT,
    methodology TEXT,
    retrieved_at TEXT,
    import_id INTEGER,
    UNIQUE (game_id, statistic_key),
    FOREIGN KEY (game_id) REFERENCES countries(game_id) ON DELETE RESTRICT,
    FOREIGN KEY (import_id) REFERENCES dataset_imports(import_id) ON DELETE RESTRICT,
    CHECK (
        (value IS NOT NULL AND value_status IN ('observed', 'estimated', 'projected'))
        OR
        (value IS NULL AND value_status IN ('unavailable', 'not_applicable'))
    )
);

INSERT INTO current_statistics_v3 (
    statistic_id, game_id, statistic_key, value, unit, observed_at,
    observation_period, value_status, import_id
)
SELECT
    statistic_id, game_id, statistic_key, value, unit, observed_at,
    observed_at, 'observed', import_id
FROM current_statistics;

DROP TABLE current_statistics;
ALTER TABLE current_statistics_v3 RENAME TO current_statistics;

ALTER TABLE selected_game_data
ADD COLUMN value_status TEXT NOT NULL DEFAULT 'observed'
CHECK (value_status IN ('observed', 'estimated', 'projected'));

ALTER TABLE selected_game_data ADD COLUMN observation_period TEXT;
ALTER TABLE selected_game_data ADD COLUMN source_reference TEXT;
ALTER TABLE selected_game_data ADD COLUMN source_version TEXT;
ALTER TABLE selected_game_data ADD COLUMN methodology TEXT;
ALTER TABLE selected_game_data ADD COLUMN retrieved_at TEXT;

CREATE INDEX ix_current_statistics_key
    ON current_statistics(statistic_key, value_status);
CREATE INDEX ix_selected_game_data_category
    ON selected_game_data(data_category, data_key, value_status);
