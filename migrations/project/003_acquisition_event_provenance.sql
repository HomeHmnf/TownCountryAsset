-- Acquisition event identity and lossless manifest integrity evidence.
ALTER TABLE acquisitions ADD COLUMN acquisition_event_key TEXT;
ALTER TABLE acquisitions ADD COLUMN manifest_sha256 TEXT
    CHECK (manifest_sha256 IS NULL OR (
        length(manifest_sha256) = 64 AND manifest_sha256 NOT GLOB '*[^0-9a-f]*'
    ));
ALTER TABLE acquisitions ADD COLUMN integrity_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (integrity_status IN ('pending', 'verified', 'failed'));
ALTER TABLE acquisitions ADD COLUMN evidence_json TEXT NOT NULL DEFAULT '{}'
    CHECK (json_valid(evidence_json) AND json_type(evidence_json) = 'object');

CREATE UNIQUE INDEX ux_acquisitions_stream_event
    ON acquisitions(stream_id, acquisition_event_key)
    WHERE acquisition_event_key IS NOT NULL;

CREATE INDEX ix_acquisitions_integrity
    ON acquisitions(integrity_status, acquired_at DESC);
