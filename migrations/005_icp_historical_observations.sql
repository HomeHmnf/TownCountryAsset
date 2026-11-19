-- ICP annual historical observations are separate from current_statistics.
-- Values are retained by persistent game identity, indicator, classification and year.
CREATE TABLE icp_historical_observations (
    observation_id INTEGER PRIMARY KEY,
    game_id TEXT NOT NULL,
    indicator_code TEXT NOT NULL CHECK (length(trim(indicator_code)) > 0),
    indicator_name TEXT NOT NULL CHECK (length(trim(indicator_name)) > 0),
    classification_code TEXT NOT NULL CHECK (length(trim(classification_code)) > 0),
    observation_year INTEGER NOT NULL CHECK (observation_year BETWEEN 1900 AND 2200),
    value REAL,
    value_status TEXT NOT NULL CHECK (value_status IN ('observed', 'source_missing')),
    missing_value_token TEXT,
    unit TEXT NOT NULL CHECK (length(trim(unit)) > 0),
    source_country_code TEXT NOT NULL CHECK (length(trim(source_country_code)) > 0),
    source_country_name TEXT NOT NULL CHECK (length(trim(source_country_name)) > 0),
    source_reference TEXT NOT NULL CHECK (length(trim(source_reference)) > 0),
    source_version TEXT NOT NULL CHECK (length(trim(source_version)) > 0),
    retrieved_at TEXT NOT NULL,
    import_id INTEGER NOT NULL,
    UNIQUE (game_id, indicator_code, classification_code, observation_year),
    FOREIGN KEY (game_id) REFERENCES countries(game_id) ON DELETE RESTRICT,
    FOREIGN KEY (import_id) REFERENCES dataset_imports(import_id) ON DELETE RESTRICT,
    CHECK (
        (value_status = 'observed' AND value IS NOT NULL AND missing_value_token IS NULL)
        OR
        (value_status = 'source_missing' AND value IS NULL AND missing_value_token = '..')
    )
);
CREATE INDEX ix_icp_history_country_year
    ON icp_historical_observations(game_id, observation_year, indicator_code);
CREATE INDEX ix_icp_history_indicator_year
    ON icp_historical_observations(indicator_code, observation_year, value_status);
