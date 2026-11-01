-- Project-wide approval gate for canonical SQLite applications.
-- Approval records contain immutable fingerprints of the reviewed application inputs.
CREATE TABLE application_approvals (
    approval_id TEXT PRIMARY KEY CHECK (length(trim(approval_id)) > 0),
    domain TEXT NOT NULL CHECK (length(trim(domain)) > 0),
    artifact_sha256 TEXT NOT NULL CHECK (
        length(artifact_sha256) = 64 AND artifact_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    artifact_json TEXT NOT NULL CHECK (json_valid(artifact_json)),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'invalidated', 'applied')),
    created_at TEXT NOT NULL,
    approved_by TEXT,
    approved_at TEXT,
    decision_note TEXT,
    applied_at TEXT,
    application_id TEXT,
    CHECK (
        (status IN ('pending', 'rejected', 'invalidated') AND approved_by IS NULL AND approved_at IS NULL)
        OR
        (status IN ('approved', 'applied') AND approved_by IS NOT NULL AND approved_at IS NOT NULL)
    ),
    CHECK (
        (status = 'applied' AND applied_at IS NOT NULL AND application_id IS NOT NULL)
        OR
        (status <> 'applied' AND applied_at IS NULL AND application_id IS NULL)
    )
);
CREATE INDEX ix_application_approvals_status
    ON application_approvals(status, created_at);

CREATE TABLE database_application_events (
    event_id INTEGER PRIMARY KEY,
    approval_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (
        event_type IN ('proposed', 'approved', 'rejected', 'invalidated', 'applied')
    ),
    event_at TEXT NOT NULL,
    actor TEXT,
    details_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(details_json)),
    FOREIGN KEY (approval_id) REFERENCES application_approvals(approval_id) ON DELETE RESTRICT
);
CREATE INDEX ix_database_application_events_approval
    ON database_application_events(approval_id, event_id);
