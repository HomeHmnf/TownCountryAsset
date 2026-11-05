-- Project source/research database schema, version 1.
-- Applied transactionally by tools.database.schema; do not add BEGIN/COMMIT here.

CREATE TABLE source_organisations (
    organisation_key TEXT PRIMARY KEY CHECK (length(trim(organisation_key)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    description TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE sources (
    source_key TEXT PRIMARY KEY CHECK (length(trim(source_key)) > 0),
    organisation_key TEXT,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    description TEXT,
    source_type TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organisation_key) REFERENCES source_organisations(organisation_key) ON DELETE RESTRICT
);
CREATE INDEX ix_sources_organisation ON sources(organisation_key);

CREATE TABLE datasets (
    dataset_id INTEGER PRIMARY KEY,
    source_key TEXT NOT NULL,
    dataset_key TEXT NOT NULL CHECK (length(trim(dataset_key)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    description TEXT,
    data_format TEXT,
    frequency TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (source_key, dataset_key),
    UNIQUE (dataset_id, source_key),
    FOREIGN KEY (source_key) REFERENCES sources(source_key) ON DELETE RESTRICT
);
CREATE INDEX ix_datasets_source ON datasets(source_key);

CREATE TABLE source_urls (
    source_url_id INTEGER PRIMARY KEY,
    source_key TEXT NOT NULL,
    dataset_id INTEGER,
    url_role TEXT NOT NULL CHECK (url_role IN (
        'homepage', 'documentation', 'dataset_page', 'api_base',
        'download', 'terms', 'licence', 'evidence', 'other'
    )),
    url TEXT NOT NULL CHECK (length(trim(url)) > 0),
    label TEXT,
    is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    valid_from TEXT,
    valid_to TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    created_at TEXT NOT NULL,
    UNIQUE (source_key, url_role, url),
    FOREIGN KEY (source_key) REFERENCES sources(source_key) ON DELETE RESTRICT,
    FOREIGN KEY (dataset_id, source_key) REFERENCES datasets(dataset_id, source_key) ON DELETE RESTRICT
);
CREATE INDEX ix_source_urls_source_role ON source_urls(source_key, url_role);
CREATE INDEX ix_source_urls_dataset ON source_urls(dataset_id);

CREATE TABLE acquisition_streams (
    stream_id INTEGER PRIMARY KEY,
    dataset_id INTEGER NOT NULL,
    stream_key TEXT NOT NULL CHECK (length(trim(stream_key)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    acquisition_mode TEXT,
    validation_contract_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(validation_contract_json)),
    retention_limit INTEGER NOT NULL DEFAULT 2 CHECK (retention_limit = 2),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (dataset_id, stream_key),
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id) ON DELETE RESTRICT
);
CREATE INDEX ix_acquisition_streams_dataset ON acquisition_streams(dataset_id);

CREATE TABLE acquisitions (
    acquisition_id INTEGER PRIMARY KEY,
    stream_id INTEGER NOT NULL,
    provider_release_id TEXT,
    acquisition_year INTEGER NOT NULL CHECK (acquisition_year BETWEEN 1900 AND 9999),
    acquired_at TEXT NOT NULL,
    provider_published_at TEXT,
    status TEXT NOT NULL DEFAULT 'candidate'
        CHECK (status IN ('candidate', 'acquired', 'validated', 'retained', 'superseded', 'failed', 'rejected')),
    acquisition_note TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (stream_id) REFERENCES acquisition_streams(stream_id) ON DELETE RESTRICT
);
CREATE INDEX ix_acquisitions_stream_status_time
    ON acquisitions(stream_id, status, acquired_at DESC, acquisition_id DESC);
CREATE INDEX ix_acquisitions_stream_release
    ON acquisitions(stream_id, provider_release_id)
    WHERE provider_release_id IS NOT NULL;

CREATE TABLE acquisition_artifacts (
    artifact_id INTEGER PRIMARY KEY,
    acquisition_id INTEGER NOT NULL,
    artifact_role TEXT NOT NULL CHECK (artifact_role IN (
        'dataset', 'metadata', 'manifest', 'supporting_document',
        'api_page', 'derivative', 'validation_report', 'other'
    )),
    relative_path TEXT NOT NULL CHECK (length(trim(relative_path)) > 0),
    sha256 TEXT NOT NULL CHECK (
        length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    byte_count INTEGER NOT NULL CHECK (byte_count >= 0),
    media_type TEXT,
    retrieval_url TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    created_at TEXT NOT NULL,
    UNIQUE (acquisition_id, relative_path),
    FOREIGN KEY (acquisition_id) REFERENCES acquisitions(acquisition_id) ON DELETE CASCADE
);
CREATE INDEX ix_acquisition_artifacts_acquisition ON acquisition_artifacts(acquisition_id);

-- A retained acquisition must already have passed validation.
CREATE TRIGGER acquisitions_retain_only_validated_insert
BEFORE INSERT ON acquisitions
WHEN NEW.status = 'retained'
BEGIN
    SELECT RAISE(ABORT, 'an acquisition must be validated before retention');
END;

CREATE TRIGGER acquisitions_retain_only_validated_update
BEFORE UPDATE OF status ON acquisitions
WHEN NEW.status = 'retained' AND OLD.status <> 'validated'
BEGIN
    SELECT RAISE(ABORT, 'only a validated acquisition can be retained');
END;

-- Retention promotion must first move an older retained acquisition out of
-- the retained state, then retain its validated replacement in the same
-- transaction. Filesystem cleanup is deliberately implemented in Stage 2.
CREATE TRIGGER acquisitions_max_two_retained_insert
BEFORE INSERT ON acquisitions
WHEN NEW.status = 'retained'
BEGIN
    SELECT RAISE(ABORT, 'acquisition must be validated before retention');
END;

CREATE TRIGGER acquisitions_max_two_retained_update
BEFORE UPDATE OF status ON acquisitions
WHEN NEW.status = 'retained'
 AND OLD.status <> 'retained'
 AND (
    SELECT COUNT(*) FROM acquisitions
    WHERE stream_id = NEW.stream_id AND status = 'retained'
 ) >= 2
BEGIN
    SELECT RAISE(ABORT, 'an acquisition stream may retain at most two versions');
END;
