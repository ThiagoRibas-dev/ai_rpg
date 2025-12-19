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
        manifest = self.get_manifest(session_id)
        missing = []
        warnings = []

        # 1. System Manifest (Mechanics)
        if not manifest.get("manifest_id"):
            missing.append("Game System (Manifest)")

        # 2. World Data
        if not manifest.get("genre"):
            missing.append("Genre")
        if not manifest.get("tone"):
            missing.append("Tone")
        if not manifest.get("starting_location"):
            missing.append("Starting Location")

        # 3. Character
        if not manifest.get("player_character"):
            # It's okay if not explicitly in setup manifest, provided entity exists
            pass

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
