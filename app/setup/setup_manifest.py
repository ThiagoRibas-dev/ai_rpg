import json
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class SetupValidation:
    """Result of manifest validation."""

    is_complete: bool
    missing_items: List[str]
    warnings: List[str]


class SetupManifest:
    """Manages the SETUP mode checklist/manifest."""

    def __init__(self, db_manager):
        self.db = db_manager

    def get_manifest(self, session_id: int) -> Dict[str, Any]:
        session = self.db.sessions.get_by_id(session_id)
        if not session.setup_phase_data:
            return self._empty_manifest()
        try:
            return json.loads(session.setup_phase_data)
        except json.JSONDecodeError:
            return self._empty_manifest()

    def update_manifest(
        self, session_id: int, updates: Dict[str, Any], merge: bool = True
    ) -> Dict[str, Any]:
        session = self.db.sessions.get_by_id(session_id)
        if merge:
            current = self.get_manifest(session_id)
            current.update(updates)
            new_manifest = current
        else:
            new_manifest = updates
        session.setup_phase_data = json.dumps(new_manifest)
        self.db.sessions.update(session)
        return new_manifest

    def validate(self, session_id: int) -> SetupValidation:
        from app.services.state_service import get_entity
        from app.prefabs.validation import validate_entity
        from app.prefabs.manifest import SystemManifest

        manifest = self.get_manifest(session_id)
        missing = []
        warnings = []

        # 1. System Manifest (Mechanics)
        manifest_id = manifest.get("manifest_id")
        sys_manifest_obj = None
        if not manifest_id:
            missing.append("Game System (Manifest ID missing)")
        else:
            sys_manifest_data = self.db.manifests.get_by_id(manifest_id)
            if not sys_manifest_data:
                missing.append("Game System (Manifest not found in DB)")
            else:
                sys_manifest_obj = SystemManifest(**sys_manifest_data) if isinstance(sys_manifest_data, dict) else sys_manifest_data

        # 2. World Data
        if not manifest.get("genre"):
            missing.append("Genre")
        if not manifest.get("tone"):
            missing.append("Tone")
            
        start_loc = manifest.get("starting_location")
        if not start_loc:
            missing.append("Starting Location")
        else:
            loc_entity = get_entity(session_id, self.db, "location", start_loc)
            if not loc_entity:
                missing.append("Starting Location (Entity not found in DB)")

        # 3. Character
        char_entity = get_entity(session_id, self.db, "character", "player")
        if not char_entity:
            missing.append("Player Character (Entity not found in DB)")
        elif sys_manifest_obj:
            _, corrections = validate_entity(char_entity, sys_manifest_obj)
            if corrections:
                warnings.append(f"Player character validation needed {len(corrections)} corrections")

        is_complete = len(missing) == 0

        return SetupValidation(is_complete, missing, warnings)

    def _empty_manifest(self) -> Dict[str, Any]:
        return {
            "genre": None,
            "tone": None,
            "player_character": None,
            "starting_location": None,
            "manifest_id": None,
        }
