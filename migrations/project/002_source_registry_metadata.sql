-- Promote frequently inspected registry fields while retaining the full
-- source configuration in metadata_json for lossless forward compatibility.
ALTER TABLE sources ADD COLUMN domains_json TEXT NOT NULL DEFAULT '[]'
    CHECK (json_valid(domains_json) AND json_type(domains_json) = 'array');
ALTER TABLE sources ADD COLUMN license_status TEXT;
ALTER TABLE sources ADD COLUMN attribution TEXT;
ALTER TABLE sources ADD COLUMN notes TEXT;
ALTER TABLE sources ADD COLUMN acquisition_mode TEXT;
ALTER TABLE sources ADD COLUMN release_discovery_json TEXT NOT NULL DEFAULT '{}'
    CHECK (json_valid(release_discovery_json) AND json_type(release_discovery_json) = 'object');
ALTER TABLE sources ADD COLUMN legacy_source_ids_json TEXT NOT NULL DEFAULT '[]'
    CHECK (json_valid(legacy_source_ids_json) AND json_type(legacy_source_ids_json) = 'array');
ALTER TABLE sources ADD COLUMN field_ids_json TEXT NOT NULL DEFAULT '[]'
    CHECK (json_valid(field_ids_json) AND json_type(field_ids_json) = 'array');
