-- Preserve annual IMF WEO source observations without coercing them into
-- current_statistics or guessing actual/estimate/projected classifications.
CREATE TABLE imf_weo_historical_observations (
    observation_id INTEGER PRIMARY KEY,
    game_id TEXT NOT NULL,
    source_country_code TEXT NOT NULL CHECK (length(trim(source_country_code)) > 0),
    source_country_name TEXT NOT NULL CHECK (length(trim(source_country_name)) > 0),
    indicator_code TEXT NOT NULL CHECK (indicator_code IN ('NGDPD', 'NGDPDPC', 'PPPGDP', 'PCPIPCH', 'LUR')),
    field_id INTEGER NOT NULL CHECK (field_id IN (15, 16, 18, 20, 21)),
    observation_year INTEGER NOT NULL CHECK (observation_year BETWEEN 1900 AND 2200),
    value REAL NOT NULL,
    unit TEXT,
    scale TEXT,
    value_status TEXT NOT NULL DEFAULT 'unclassified'
        CHECK (value_status IN ('unclassified', 'observed', 'estimated', 'projected')),
    latest_actual_annual_data TEXT,
    reporting_year_months TEXT,
    source_reference TEXT NOT NULL CHECK (length(trim(source_reference)) > 0),
    source_version TEXT NOT NULL CHECK (length(trim(source_version)) > 0),
    source_sha256 TEXT NOT NULL CHECK (length(source_sha256) = 64 AND source_sha256 NOT GLOB '*[^0-9a-f]*'),
    acquired_on TEXT NOT NULL,
    acquisition_time_precision TEXT NOT NULL CHECK (acquisition_time_precision IN ('day', 'timestamp')),
    import_id INTEGER NOT NULL,
    UNIQUE (game_id, indicator_code, observation_year, source_version),
    FOREIGN KEY (game_id) REFERENCES countries(game_id) ON DELETE RESTRICT,
    FOREIGN KEY (import_id) REFERENCES dataset_imports(import_id) ON DELETE RESTRICT
);
CREATE INDEX ix_imf_weo_history_game_year
    ON imf_weo_historical_observations(game_id, observation_year, field_id);
CREATE INDEX ix_imf_weo_history_indicator_year
    ON imf_weo_historical_observations(indicator_code, observation_year, value_status);
