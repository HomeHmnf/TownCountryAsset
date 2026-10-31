-- TownCountryAsset canonical SQLite schema, version 1.
-- Applied transactionally by tools.database.schema; do not add BEGIN/COMMIT here.

CREATE TABLE dataset_imports (
    import_id INTEGER PRIMARY KEY,
    dataset TEXT NOT NULL CHECK (length(trim(dataset)) > 0),
    source_version TEXT,
    source_url TEXT,
    retrieval_date TEXT,
    sha256 TEXT NOT NULL CHECK (
        length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    attribution TEXT,
    license TEXT,
    import_status TEXT NOT NULL DEFAULT 'candidate'
        CHECK (import_status IN ('candidate', 'approved', 'rejected')),
    imported_at TEXT NOT NULL
);

CREATE TABLE countries (
    game_id TEXT PRIMARY KEY CHECK (
        length(game_id) = 35
        AND substr(game_id, 1, 3) = 'tc_'
        AND substr(game_id, 4) NOT GLOB '*[^0-9a-f]*'
    ),
    entity_type TEXT NOT NULL DEFAULT 'unreviewed',
    record_status TEXT NOT NULL DEFAULT 'candidate'
        CHECK (record_status IN ('candidate', 'approved', 'rejected', 'retired')),
    iso_alpha2 TEXT CHECK (
        iso_alpha2 IS NULL OR (
            length(iso_alpha2) = 2 AND iso_alpha2 NOT GLOB '*[^A-Z]*'
        )
    ),
    iso_alpha3 TEXT CHECK (
        iso_alpha3 IS NULL OR (
            length(iso_alpha3) = 3 AND iso_alpha3 NOT GLOB '*[^A-Z]*'
        )
    ),
    iso_assignment_status TEXT NOT NULL DEFAULT 'unverified'
        CHECK (iso_assignment_status IN ('unverified', 'verified', 'not_applicable')),
    localization_status TEXT NOT NULL DEFAULT 'unreviewed'
        CHECK (localization_status IN ('unreviewed', 'reviewed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE country_sources (
    game_id TEXT NOT NULL,
    dataset TEXT NOT NULL,
    source_id TEXT NOT NULL CHECK (length(trim(source_id)) > 0),
    is_current INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0, 1)),
    import_id INTEGER NOT NULL,
    PRIMARY KEY (game_id, dataset, source_id),
    FOREIGN KEY (game_id) REFERENCES countries(game_id) ON DELETE RESTRICT,
    FOREIGN KEY (import_id) REFERENCES dataset_imports(import_id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX uq_current_country_source
    ON country_sources(dataset, source_id) WHERE is_current = 1;
CREATE INDEX ix_country_sources_game ON country_sources(game_id, dataset);

CREATE TABLE country_names (
    name_id INTEGER PRIMARY KEY,
    game_id TEXT NOT NULL,
    language TEXT NOT NULL CHECK (length(trim(language)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    name_type TEXT NOT NULL CHECK (name_type IN ('canonical', 'alias')),
    FOREIGN KEY (game_id) REFERENCES countries(game_id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX uq_country_canonical_name
    ON country_names(game_id, language) WHERE name_type = 'canonical';
CREATE UNIQUE INDEX uq_country_name_value
    ON country_names(game_id, language, name, name_type);
CREATE INDEX ix_country_names_lookup ON country_names(language, name);

CREATE TABLE country_regions (
    game_id TEXT NOT NULL,
    region TEXT NOT NULL CHECK (length(trim(region)) > 0),
    classification_source TEXT NOT NULL DEFAULT 'config',
    PRIMARY KEY (game_id, region),
    FOREIGN KEY (game_id) REFERENCES countries(game_id) ON DELETE RESTRICT
);

CREATE TABLE country_attributes (
    game_id TEXT NOT NULL,
    attribute_key TEXT NOT NULL CHECK (length(trim(attribute_key)) > 0),
    attribute_value TEXT,
    value_type TEXT NOT NULL CHECK (
        value_type IN ('null', 'text', 'integer', 'real', 'boolean', 'json')
    ),
    PRIMARY KEY (game_id, attribute_key),
    CHECK (
        (value_type = 'null' AND attribute_value IS NULL)
        OR (value_type <> 'null' AND attribute_value IS NOT NULL)
    ),
    CHECK (value_type <> 'json' OR json_valid(attribute_value)),
    FOREIGN KEY (game_id) REFERENCES countries(game_id) ON DELETE RESTRICT
);

CREATE TABLE country_geometries (
    game_id TEXT NOT NULL,
    profile TEXT NOT NULL CHECK (profile IN ('low', 'medium', 'high')),
    geometry_json TEXT NOT NULL CHECK (json_valid(geometry_json)),
    sha256 TEXT NOT NULL CHECK (
        length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    import_id INTEGER NOT NULL,
    PRIMARY KEY (game_id, profile),
    FOREIGN KEY (game_id) REFERENCES countries(game_id) ON DELETE RESTRICT,
    FOREIGN KEY (import_id) REFERENCES dataset_imports(import_id) ON DELETE RESTRICT
);

CREATE TABLE import_runs (
    run_id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    source_sha256 TEXT CHECK (
        source_sha256 IS NULL OR (
            length(source_sha256) = 64 AND source_sha256 NOT GLOB '*[^0-9a-f]*'
        )
    ),
    error_message TEXT,
    CHECK (completed_at IS NULL OR completed_at >= started_at),
    CHECK (
        (status = 'running' AND completed_at IS NULL)
        OR (status IN ('succeeded', 'failed') AND completed_at IS NOT NULL)
    )
);

CREATE TABLE current_statistics (
    statistic_id INTEGER PRIMARY KEY,
    game_id TEXT NOT NULL,
    statistic_key TEXT NOT NULL CHECK (length(trim(statistic_key)) > 0),
    value REAL NOT NULL,
    unit TEXT,
    observed_at TEXT NOT NULL,
    import_id INTEGER,
    UNIQUE (game_id, statistic_key),
    FOREIGN KEY (game_id) REFERENCES countries(game_id) ON DELETE RESTRICT,
    FOREIGN KEY (import_id) REFERENCES dataset_imports(import_id) ON DELETE RESTRICT
);

CREATE TABLE selected_game_data (
    game_data_id INTEGER PRIMARY KEY,
    game_id TEXT NOT NULL,
    data_category TEXT NOT NULL CHECK (length(trim(data_category)) > 0),
    data_key TEXT NOT NULL CHECK (length(trim(data_key)) > 0),
    payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
    import_id INTEGER,
    UNIQUE (game_id, data_category, data_key),
    FOREIGN KEY (game_id) REFERENCES countries(game_id) ON DELETE RESTRICT,
    FOREIGN KEY (import_id) REFERENCES dataset_imports(import_id) ON DELETE RESTRICT
);

CREATE TABLE country_flags (
    game_id TEXT PRIMARY KEY,
    source_flag_code TEXT,
    mapping_status TEXT NOT NULL DEFAULT 'candidate'
        CHECK (mapping_status IN ('candidate', 'reviewed', 'rejected')),
    decision_note TEXT,
    evidence_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_json)),
    FOREIGN KEY (game_id) REFERENCES countries(game_id) ON DELETE RESTRICT
);

CREATE TABLE review_proposals (
    proposal_id INTEGER PRIMARY KEY,
    game_id TEXT NOT NULL,
    proposal_type TEXT NOT NULL CHECK (
        proposal_type IN ('iso', 'localization', 'entity_type', 'flag')
    ),
    proposal_fingerprint TEXT NOT NULL CHECK (
        length(proposal_fingerprint) = 64
        AND proposal_fingerprint NOT GLOB '*[^0-9a-f]*'
    ),
    proposed_json TEXT NOT NULL CHECK (json_valid(proposed_json)),
    evidence_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_json)),
    review_status TEXT NOT NULL DEFAULT 'candidate'
        CHECK (review_status IN ('candidate', 'approved', 'rejected')),
    created_at TEXT NOT NULL,
    reviewed_at TEXT,
    UNIQUE (game_id, proposal_type, proposal_fingerprint),
    FOREIGN KEY (game_id) REFERENCES countries(game_id) ON DELETE RESTRICT,
    CHECK (review_status <> 'approved' OR reviewed_at IS NOT NULL)
);
CREATE INDEX ix_review_proposals_game
    ON review_proposals(game_id, proposal_type, review_status);

CREATE TRIGGER countries_verified_iso_insert
BEFORE INSERT ON countries
WHEN NEW.iso_assignment_status = 'verified'
 AND (NEW.iso_alpha2 IS NULL OR NEW.iso_alpha3 IS NULL)
BEGIN
    SELECT RAISE(ABORT, 'verified ISO assignment requires alpha-2 and alpha-3');
END;

CREATE TRIGGER countries_verified_iso_update
BEFORE UPDATE OF iso_assignment_status, iso_alpha2, iso_alpha3 ON countries
WHEN NEW.iso_assignment_status = 'verified'
 AND (NEW.iso_alpha2 IS NULL OR NEW.iso_alpha3 IS NULL)
BEGIN
    SELECT RAISE(ABORT, 'verified ISO assignment requires alpha-2 and alpha-3');
END;

CREATE TRIGGER review_proposals_approved_insert
BEFORE INSERT ON review_proposals
WHEN NEW.review_status = 'approved' AND NEW.reviewed_at IS NULL
BEGIN
    SELECT RAISE(ABORT, 'approved proposal requires reviewed_at');
END;

CREATE TRIGGER review_proposals_approved_update
BEFORE UPDATE OF review_status, reviewed_at ON review_proposals
WHEN NEW.review_status = 'approved' AND NEW.reviewed_at IS NULL
BEGIN
    SELECT RAISE(ABORT, 'approved proposal requires reviewed_at');
END;

CREATE TRIGGER country_flags_reviewed_insert
BEFORE INSERT ON country_flags
WHEN NEW.mapping_status = 'reviewed'
 AND NOT EXISTS (
     SELECT 1 FROM review_proposals p
     WHERE p.game_id = NEW.game_id
       AND p.proposal_type = 'flag'
       AND p.review_status = 'approved'
 )
BEGIN
    SELECT RAISE(ABORT, 'reviewed flag requires an approved flag proposal');
END;

CREATE TRIGGER country_flags_reviewed_update
BEFORE UPDATE OF mapping_status ON country_flags
WHEN NEW.mapping_status = 'reviewed'
 AND NOT EXISTS (
     SELECT 1 FROM review_proposals p
     WHERE p.game_id = NEW.game_id
       AND p.proposal_type = 'flag'
       AND p.review_status = 'approved'
 )
BEGIN
    SELECT RAISE(ABORT, 'reviewed flag requires an approved flag proposal');
END;
