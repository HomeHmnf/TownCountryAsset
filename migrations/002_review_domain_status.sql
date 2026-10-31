-- WP1.4 review-domain constraints. Applied transactionally by the migration manager.
ALTER TABLE countries
ADD COLUMN entity_type_status TEXT NOT NULL DEFAULT 'unreviewed'
CHECK (entity_type_status IN ('unreviewed', 'reviewed'));

CREATE TRIGGER countries_entity_type_reviewed_insert
BEFORE INSERT ON countries
WHEN NEW.entity_type_status = 'reviewed'
 AND NOT EXISTS (
     SELECT 1 FROM review_proposals p
     WHERE p.game_id = NEW.game_id
       AND p.proposal_type = 'entity_type'
       AND p.review_status = 'approved'
       AND json_extract(p.proposed_json, '$.entity_type') = NEW.entity_type
 )
BEGIN
    SELECT RAISE(ABORT, 'reviewed entity type requires a matching approved entity_type proposal');
END;

CREATE TRIGGER countries_entity_type_reviewed_update
BEFORE UPDATE OF entity_type, entity_type_status ON countries
WHEN NEW.entity_type_status = 'reviewed'
 AND NOT EXISTS (
     SELECT 1 FROM review_proposals p
     WHERE p.game_id = NEW.game_id
       AND p.proposal_type = 'entity_type'
       AND p.review_status = 'approved'
       AND json_extract(p.proposed_json, '$.entity_type') = NEW.entity_type
 )
BEGIN
    SELECT RAISE(ABORT, 'reviewed entity type requires a matching approved entity_type proposal');
END;

CREATE TRIGGER countries_localization_reviewed_insert
BEFORE INSERT ON countries
WHEN NEW.localization_status = 'reviewed'
 AND NOT EXISTS (
     SELECT 1 FROM review_proposals p
     WHERE p.game_id = NEW.game_id
       AND p.proposal_type = 'localization'
       AND p.review_status = 'approved'
       AND json_extract(p.proposed_json, '$.language') = 'fa'
       AND json_extract(p.proposed_json, '$.name') IS NOT NULL
 )
BEGIN
    SELECT RAISE(ABORT, 'reviewed localization requires an approved Persian localization proposal');
END;

CREATE TRIGGER countries_localization_reviewed_update
BEFORE UPDATE OF localization_status ON countries
WHEN NEW.localization_status = 'reviewed'
 AND NOT EXISTS (
     SELECT 1 FROM review_proposals p
     WHERE p.game_id = NEW.game_id
       AND p.proposal_type = 'localization'
       AND p.review_status = 'approved'
       AND json_extract(p.proposed_json, '$.language') = 'fa'
       AND json_extract(p.proposed_json, '$.name') IS NOT NULL
 )
BEGIN
    SELECT RAISE(ABORT, 'reviewed localization requires an approved Persian localization proposal');
END;

CREATE TRIGGER countries_verified_iso_approved_insert
BEFORE INSERT ON countries
WHEN NEW.iso_assignment_status = 'verified'
 AND NOT EXISTS (
     SELECT 1 FROM review_proposals p
     WHERE p.game_id = NEW.game_id
       AND p.proposal_type = 'iso'
       AND p.review_status = 'approved'
       AND json_extract(p.proposed_json, '$.alpha2') = NEW.iso_alpha2
       AND json_extract(p.proposed_json, '$.alpha3') = NEW.iso_alpha3
 )
BEGIN
    SELECT RAISE(ABORT, 'verified ISO assignment requires a matching approved ISO proposal');
END;

CREATE TRIGGER countries_verified_iso_approved_update
BEFORE UPDATE OF iso_assignment_status, iso_alpha2, iso_alpha3 ON countries
WHEN NEW.iso_assignment_status = 'verified'
 AND NOT EXISTS (
     SELECT 1 FROM review_proposals p
     WHERE p.game_id = NEW.game_id
       AND p.proposal_type = 'iso'
       AND p.review_status = 'approved'
       AND json_extract(p.proposed_json, '$.alpha2') = NEW.iso_alpha2
       AND json_extract(p.proposed_json, '$.alpha3') = NEW.iso_alpha3
 )
BEGIN
    SELECT RAISE(ABORT, 'verified ISO assignment requires a matching approved ISO proposal');
END;
