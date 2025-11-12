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
    
    REQUIRED_FIELDS = [
        "genre",
        "tone", 
        "core_properties",
        "player_character",
        "starting_location",
        "ready_to_play"
    ]
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def get_manifest(self, session_id: int) -> Dict[str, Any]:
        """Get current setup manifest."""
        session = self.db.load_session(session_id)
        
        if not session.setup_phase_data:
            # Initialize if empty
            return self._empty_manifest()
        
        try:
            return json.loads(session.setup_phase_data)
        except json.JSONDecodeError:
            return self._empty_manifest()
    
    def update_manifest(
        self, 
        session_id: int, 
        updates: Dict[str, Any],
        merge: bool = True
    ) -> Dict[str, Any]:
        """
        Update the setup manifest.
        
        Args:
            session_id: Session ID
            updates: Fields to update
            merge: If True, merge with existing. If False, replace.
        
        Returns:
            Updated manifest
        """
        session = self.db.load_session(session_id)
        
        if merge:
            current = self.get_manifest(session_id)
            current.update(updates)
            new_manifest = current
        else:
            new_manifest = updates
        
        session.setup_phase_data = json.dumps(new_manifest)
        self.db.update_session(session)
        
        return new_manifest
    
    def validate(self, session_id: int) -> SetupValidation:
        """
        Validate if setup manifest is complete.
        
        Returns:
            SetupValidation with completion status and missing items
        """
        manifest = self.get_manifest(session_id)
        missing = []
        warnings = []
        
        # Check genre
        if not manifest.get("genre"):
            missing.append("genre (game setting/type)")
        
        # Check tone
        if not manifest.get("tone"):
            missing.append("tone (atmosphere/style)")
        
        # Check core properties (need at least 3)
        props = manifest.get("core_properties", [])
        if not props:
            missing.append("core_properties (character attributes)")
        elif len(props) < 3:
            warnings.append(f"Only {len(props)} properties defined (recommend 3-5)")
        
        # Verify properties actually exist in schema
        if props:
            schema = self.db.get_schema_extensions(session_id, "character")
            undefined = [p for p in props if p not in schema]
            if undefined:
                warnings.append(
                    f"Properties in manifest but not in schema: {', '.join(undefined)}"
                )
        
        # Check player character
        if not manifest.get("player_character"):
            missing.append("player_character (protagonist)")
        else:
            # Verify character entity exists
            char_key = manifest["player_character"]
            if isinstance(char_key, dict):
                char_key = char_key.get("key", "player")
            
            char_data = self.db.get_game_state_entity(session_id, "character", char_key)
            if not char_data:
                warnings.append(
                    f"Character '{char_key}' in manifest but not found in game state"
                )
        
        # Check starting location
        if not manifest.get("starting_location"):
            missing.append("starting_location (where story begins)")
        else:
            # Verify location entity exists
            loc_key = manifest["starting_location"]
            if isinstance(loc_key, dict):
                loc_key = loc_key.get("key")
            
            if loc_key:
                loc_data = self.db.get_game_state_entity(session_id, "location", loc_key)
                if not loc_data:
                    warnings.append(
                        f"Location '{loc_key}' in manifest but not found in game state"
                    )
        
        # Check ready flag
        if not manifest.get("ready_to_play"):
            missing.append("ready_to_play (player confirmation)")
        
        is_complete = len(missing) == 0
        
        return SetupValidation(
            is_complete=is_complete,
            missing_items=missing,
            warnings=warnings
        )
    
    def get_progress_summary(self, session_id: int) -> str:
        """Get human-readable progress summary."""
        manifest = self.get_manifest(session_id)
        validation = self.validate(session_id)
        
        lines = ["📋 SETUP PROGRESS:"]
        
        # Genre
        genre = manifest.get("genre")
        if genre:
            desc = genre if isinstance(genre, str) else genre.get("description", "Defined")
            lines.append(f"  ✅ Genre: {desc}")
        else:
            lines.append("  ❌ Genre: Not defined")
        
        # Tone
        tone = manifest.get("tone")
        if tone:
            desc = tone if isinstance(tone, str) else tone.get("description", "Defined")
            lines.append(f"  ✅ Tone: {desc}")
        else:
            lines.append("  ❌ Tone: Not defined")
        
        # Properties
        props = manifest.get("core_properties", [])
        if props:
            lines.append(f"  ✅ Properties: {len(props)} defined ({', '.join(props)})")
        else:
            lines.append("  ❌ Properties: None defined")
        
        # Character
        char = manifest.get("player_character")
        if char:
            if isinstance(char, dict):
                name = char.get("name", "Defined")
                lines.append(f"  ✅ Character: {name}")
            else:
                lines.append("  ✅ Character: Created")
        else:
            lines.append("  ❌ Character: Not created")
        
        # Location
        loc = manifest.get("starting_location")
        if loc:
            if isinstance(loc, dict):
                name = loc.get("name", "Defined")
                lines.append(f"  ✅ Location: {name}")
            else:
                lines.append("  ✅ Location: Created")
        else:
            lines.append("  ❌ Location: Not defined")
        
        # Ready flag
        if manifest.get("ready_to_play"):
            lines.append("  ✅ Player confirmed ready")
        else:
            lines.append("  ❌ Awaiting player confirmation")
        
        # Summary
        if validation.is_complete:
            lines.append("\n🎉 SETUP COMPLETE - Ready to play!")
        else:
            lines.append(f"\n⏳ Still needed: {', '.join(validation.missing_items)}")
        
        if validation.warnings:
            lines.append(f"\n⚠️  Warnings: {'; '.join(validation.warnings)}")
        
        return "\n".join(lines)
    
    def _empty_manifest(self) -> Dict[str, Any]:
        """Return empty manifest template."""
        return {
            "genre": None,
            "tone": None,
            "core_properties": [],
            "player_character": None,
            "starting_location": None,
            "ready_to_play": False
        }