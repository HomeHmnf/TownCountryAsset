-- Explicit, auditable decisions for identity review domains and catalogue scope.
-- Decision rows are append-only; later decisions retain prior rationale.
CREATE TABLE country_review_decisions (
    decision_id INTEGER PRIMARY KEY,
    game_id TEXT NOT NULL,
    decision_domain TEXT NOT NULL CHECK (
        decision_domain IN ('iso', 'entity_type', 'flag', 'catalogue_scope', 'naming')
    ),
    decision_code TEXT NOT NULL CHECK (length(trim(decision_code)) > 0),
    decision_status TEXT NOT NULL CHECK (
        decision_status IN ('approved', 'not_applicable', 'unresolved', 'excluded')
    ),
    decision_json TEXT NOT NULL CHECK (json_valid(decision_json)),
    evidence_json TEXT NOT NULL CHECK (json_valid(evidence_json)),
    decision_fingerprint TEXT NOT NULL CHECK (
        length(decision_fingerprint) = 64
        AND decision_fingerprint NOT GLOB '*[^0-9a-f]*'
    ),
    actor TEXT NOT NULL CHECK (length(trim(actor)) > 0),
    decided_at TEXT NOT NULL,
    approval_id TEXT NOT NULL,
    UNIQUE (game_id, decision_domain, decision_fingerprint),
    FOREIGN KEY (game_id) REFERENCES countries(game_id) ON DELETE RESTRICT,
    FOREIGN KEY (approval_id) REFERENCES application_approvals(approval_id) ON DELETE RESTRICT
);
CREATE INDEX ix_country_review_decisions_game
    ON country_review_decisions(game_id, decision_domain, decided_at);
CREATE INDEX ix_country_review_decisions_approval
    ON country_review_decisions(approval_id);

CREATE TRIGGER country_review_decisions_no_update
BEFORE UPDATE ON country_review_decisions
BEGIN
    SELECT RAISE(ABORT, 'country review decisions are append-only');
END;

CREATE TRIGGER country_review_decisions_no_delete
BEFORE DELETE ON country_review_decisions
BEGIN
    SELECT RAISE(ABORT, 'country review decisions are append-only');
END;
