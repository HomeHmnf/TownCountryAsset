-- Expose official ISO identity separately from reviewable ISO proposals.
-- A proposal remains a proposal even after its review record is persisted/applied.
CREATE VIEW country_iso_identity AS
SELECT
    c.game_id,
    c.iso_assignment_status,
    CASE WHEN c.iso_assignment_status = 'verified'
         THEN c.iso_alpha2 ELSE NULL END AS official_iso_alpha2,
    CASE WHEN c.iso_assignment_status = 'verified'
         THEN c.iso_alpha3 ELSE NULL END AS official_iso_alpha3,
    p.proposal_id AS iso_proposal_id,
    json_extract(p.proposed_json, '$.alpha2') AS proposed_iso_alpha2,
    json_extract(p.proposed_json, '$.alpha3') AS proposed_iso_alpha3,
    p.review_status AS iso_proposal_status,
    p.created_at AS iso_proposal_created_at,
    p.reviewed_at AS iso_proposal_reviewed_at
FROM countries AS c
LEFT JOIN review_proposals AS p
    ON p.proposal_id = (
        SELECT p2.proposal_id
        FROM review_proposals AS p2
        WHERE p2.game_id = c.game_id
          AND p2.proposal_type = 'iso'
        ORDER BY p2.created_at DESC, p2.proposal_id DESC
        LIMIT 1
    );
