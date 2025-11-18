import json
import logging
from app.models.ruleset import Ruleset
from app.models.stat_block import StatBlockTemplate, AbilityDef, VitalDef, SlotDef
from app.setup.setup_manifest import SetupManifest

logger = logging.getLogger(__name__)

def _get_default_scaffolding():
    """Returns a minimal default Ruleset and Template for raw prompts."""
    ruleset = Ruleset(
        meta={"name": "Default System", "genre": "Generic"},
        resolution_mechanic="Narrative / Freeform",
    )
    
    template = StatBlockTemplate(
        template_name="Adventurer",
        abilities=[
            AbilityDef(name="Strength", default=10, data_type="integer"),
            AbilityDef(name="Agility", default=10, data_type="integer"),
            AbilityDef(name="Mind", default=10, data_type="integer"),
        ],
        vitals=[
            VitalDef(name="HP", min_value=0, max_formula="10")
        ],
        slots=[
            SlotDef(name="Inventory", fixed_capacity=10)
        ]
    )
    return ruleset, template

def inject_setup_scaffolding(session_id: int, prompt_manifest_json: str, db_manager):
    """
    Inject initial scaffolding. Falls back to defaults if manifest is empty.
    """
    ruleset_model = None
    st_model = None

    # 1. Try to parse Prompt Manifest
    if prompt_manifest_json and prompt_manifest_json != "{}":
        try:
            data = json.loads(prompt_manifest_json)
            if data.get("ruleset") and data.get("stat_template"):
                ruleset_model = Ruleset(**data["ruleset"])
                st_model = StatBlockTemplate(**data["stat_template"])
        except Exception as e:
            logger.error(f"Manifest parse error: {e}. Using defaults.")

    # 2. Fallback if missing
    if not ruleset_model or not st_model:
        logger.warning("No valid manifest found. Using default scaffolding.")
        ruleset_model, st_model = _get_default_scaffolding()

    try:
        # 3. Create Active Records
        rs_id = db_manager.rulesets.create(ruleset_model)
        st_id = db_manager.stat_templates.create(rs_id, st_model)
        
        logger.info(f"Scaffolding: Ruleset {rs_id}, Template {st_id}")

        # 4. Update Session Manifest
        manifest_mgr = SetupManifest(db_manager)
        manifest_mgr.update_manifest(session_id, {
            "ruleset_id": rs_id, 
            "stat_template_id": st_id,
            "genre": ruleset_model.meta.get("genre", "Generic"),
            "tone": ruleset_model.meta.get("tone", "Neutral")
        })

        # 5. Instantiate Player
        abilities = {a.name: a.default for a in st_model.abilities}
        vitals = {}
        for v in st_model.vitals:
            # Default to max=10 if not calculable yet
            vitals[v.name] = {"current": 10, "max": 10} 
            
        tracks = {t.name: 0 for t in st_model.tracks}
        slots = {s.name: [] for s in st_model.slots}

        player_data = {
            "name": "Player",
            "template_id": st_id,
            "abilities": abilities,
            "vitals": vitals,
            "tracks": tracks,
            "slots": slots,
            "conditions": []
        }

        db_manager.game_state.set_entity(session_id, "character", "player", player_data)
        
    except Exception as e:
        logger.error(f"Error during scaffolding injection: {e}", exc_info=True)
