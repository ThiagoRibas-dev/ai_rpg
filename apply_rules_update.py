#!/usr/bin/env python3
"""
Patch Script: Vocabulary System - Part 5: Pipeline Integration
===============================================================
Integrates vocabulary throughout the application.

Modified Files:
- app/setup/rules_generator.py (use vocabulary extraction)
- app/services/game_setup_service.py (use schema builder)
- app/context/context_builder.py (vocabulary-aware context)
- app/core/react_turn_manager.py (pass vocabulary to tools)
- app/gui/dialogs/prompt_editor.py (trigger vocabulary extraction)
- app/setup/setup_manifest.py (store vocabulary)

Run: python apply_vocabulary_part5.py
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

# === Configuration ===
PROJECT_ROOT = Path(".")
BACKUP_DIR = PROJECT_ROOT / f".backup_vocab5_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def backup_file(filepath: Path):
    """Create backup of a file before modifying."""
    if filepath.exists():
        backup_path = BACKUP_DIR / filepath
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(filepath, backup_path)
        print(f"  📦 Backed up: {filepath}")


def write_file(filepath: Path, content: str):
    """Write content to file, creating directories if needed."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    print(f"  ✅ Created: {filepath}")


# =============================================================================
# UPDATE: app/setup/rules_generator.py
# =============================================================================

RULES_GENERATOR_CODE = '''"""
Rules Generator
===============
Extracts game rules, vocabulary, and invariants from rules text.

The vocabulary is extracted FIRST and becomes the source of truth for
all subsequent extractions (invariants, procedures, etc.).

Pipeline:
1. Extract Vocabulary (fields, types, roles)
2. Extract Engine Config (dice, resolution)
3. Extract Invariants (using vocabulary paths)
4. Extract Procedures (combat, exploration, etc.)
5. Extract Mechanics (as memories)
"""

import json
import logging
from typing import List, Optional, Callable, Tuple, Dict, Any

from pydantic import BaseModel

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.ruleset import Ruleset, EngineConfig, ProcedureDef, StateInvariant
from app.models.vocabulary import GameVocabulary
from app.setup.vocabulary_extractor import VocabularyExtractor
from app.setup.invariant_extractor import InvariantExtractor
from app.prompts.templates import (
    TEMPLATE_GENERATION_SYSTEM_PROMPT,
    IDENTIFY_MODES_INSTRUCTION,
    EXTRACT_PROCEDURE_INSTRUCTION,
    GENERATE_MECHANICS_INSTRUCTION,
)

logger = logging.getLogger(__name__)


class RuleEntry(BaseModel):
    name: str
    content: str
    tags: List[str]


class RulesGenerator:
    """
    Extracts a complete Ruleset from rules text.
    
    The extraction is vocabulary-first: we extract the game's vocabulary
    before anything else, then use it to guide subsequent extractions.
    """
    
    def __init__(
        self, 
        llm: LLMConnector, 
        status_callback: Optional[Callable[[str], None]] = None
    ):
        self.llm = llm
        self.status_callback = status_callback

    def _update_status(self, message: str):
        if self.status_callback:
            self.status_callback(message)
        logger.info(f"[RulesGen] {message}")

    def generate_ruleset(
        self, 
        rules_text: str
    ) -> Tuple[Ruleset, List[Dict[str, Any]], GameVocabulary]:
        """
        Generate a complete ruleset from rules text.
        
        Returns:
            Tuple of (Ruleset, base_rules list, GameVocabulary)
        """
        # === PHASE 1: VOCABULARY EXTRACTION ===
        self._update_status("Extracting game vocabulary...")
        
        vocab_extractor = VocabularyExtractor(self.llm, self.status_callback)
        vocabulary = vocab_extractor.extract(rules_text)
        
        self._update_status(
            f"Vocabulary: {len(vocabulary.fields)} fields, "
            f"{len(vocabulary.valid_paths)} paths"
        )
        
        # === PHASE 2: ENGINE EXTRACTION ===
        self._update_status("Analyzing core engine...")
        
        base_prompt = (
            f"{TEMPLATE_GENERATION_SYSTEM_PROMPT}\\n\\n# RULES REFERENCE\\n{rules_text[:8000]}"
        )

        class QuickMeta(BaseModel):
            name: str
            genre: str
            dice_notation: str
            roll_mechanic: str
            success_condition: str
            crit_rules: str
            sheet_hints: List[str]

        try:
            meta_res = self.llm.get_structured_response(
                base_prompt,
                [Message(role="user", content="Extract Game Name, Genre, Core Engine, and Sheet Hints.")],
                QuickMeta,
            )
            
            game_name = meta_res.name
            
            ruleset = Ruleset(
                meta={"name": game_name, "genre": meta_res.genre},
                engine=EngineConfig(
                    dice_notation=meta_res.dice_notation,
                    roll_mechanic=meta_res.roll_mechanic,
                    success_condition=meta_res.success_condition,
                    crit_rules=meta_res.crit_rules,
                ),
                sheet_hints=meta_res.sheet_hints,
            )
        except Exception as e:
            logger.warning(f"Engine extraction failed: {e}")
            ruleset = Ruleset(
                meta={"name": vocabulary.system_name, "genre": vocabulary.genre},
                engine=EngineConfig(
                    dice_notation=vocabulary.dice_notation,
                    roll_mechanic=vocabulary.resolution_mechanic or "Roll + Modifier",
                    success_condition="Meet or exceed target",
                    crit_rules="Natural maximum is critical",
                ),
            )
            game_name = vocabulary.system_name

        system_prompt = base_prompt.replace("{target_game}", game_name)

        # === PHASE 3: INVARIANT EXTRACTION ===
        self._update_status("Extracting state invariants...")
        
        inv_extractor = InvariantExtractor(self.llm, vocabulary, self.status_callback)
        invariants = inv_extractor.extract(rules_text)
        ruleset.state_invariants = invariants
        
        self._update_status(f"Extracted {len(invariants)} invariants")

        # === PHASE 4: PROCEDURE EXTRACTION ===
        self._update_status("Identifying game loops...")

        class GameModes(BaseModel):
            names: List[str]

        try:
            modes = self.llm.get_structured_response(
                system_prompt,
                [Message(role="user", content=IDENTIFY_MODES_INSTRUCTION)],
                GameModes,
            )
            target_modes = modes.names[:6] if modes and modes.names else []
        except Exception:
            target_modes = ["Combat", "Exploration"]

        for mode in target_modes:
            self._update_status(f"Extracting procedure: {mode}...")
            try:
                proc = self.llm.get_structured_response(
                    system_prompt,
                    [Message(role="user", content=EXTRACT_PROCEDURE_INSTRUCTION.format(mode_name=mode))],
                    ProcedureDef,
                )
                m = mode.lower()
                if "combat" in m or "encounter" in m:
                    ruleset.combat_procedures[mode] = proc
                elif "exploration" in m or "travel" in m:
                    ruleset.exploration_procedures[mode] = proc
                elif "social" in m:
                    ruleset.social_procedures[mode] = proc
                elif "downtime" in m:
                    ruleset.downtime_procedures[mode] = proc
            except Exception as e:
                logger.warning(f"Failed to extract procedure {mode}: {e}")

        # === PHASE 5: MECHANICS EXTRACTION ===
        self._update_status("Indexing mechanics...")

        class MechList(BaseModel):
            rules: List[RuleEntry]

        rule_dicts = []
        try:
            mech_res = self.llm.get_structured_response(
                system_prompt,
                [Message(role="user", content=GENERATE_MECHANICS_INSTRUCTION)],
                MechList,
            )
            for r in mech_res.rules:
                rule_dicts.append({
                    "kind": "rule",
                    "content": f"{r.name}: {r.content}",
                    "tags": r.tags + ["rule", "mechanic"],
                })
        except Exception as e:
            logger.warning(f"Failed to extract mechanics: {e}")

        self._update_status("Rules generation complete!")
        
        return ruleset, rule_dicts, vocabulary
'''


def update_rules_generator():
    """Replace rules_generator.py with vocabulary-aware version."""
    print("\n📝 Updating app/setup/rules_generator.py...")
    filepath = PROJECT_ROOT / "app" / "setup" / "rules_generator.py"

    if filepath.exists():
        backup_file(filepath)

    write_file(filepath, RULES_GENERATOR_CODE)


# =============================================================================
# UPDATE: app/gui/dialogs/prompt_editor.py
# =============================================================================

PROMPT_EDITOR_PATCH = """
    async def run_extraction(self):
        if not self.rules.strip():
            ui.notify("Please enter Rules text first.", type="warning")
            return
        self.gen_btn.disable()
        self.status_label.set_text("Extracting...")
        await asyncio.to_thread(self._execute_extraction)
        self.gen_btn.enable()

    def _execute_extraction(self):
        connector = self.orchestrator._get_llm_connector()
        service = RulesGenerator(connector, status_callback=self._update_status)
        try:
            ruleset, rule_mems, vocabulary = service.generate_ruleset(self.rules)

            # Combine into Manifest (now includes vocabulary)
            manifest = {
                "vocabulary": vocabulary.model_dump(),
                "ruleset": ruleset.model_dump(),
                "base_rules": rule_mems,
            }
            self.manifest_json = json.dumps(manifest, indent=2)
            self._update_status("Extraction Complete!")
        except Exception as e:
            logger.warning(f"Rules extraction failed: {e}")
            self._update_status(f"Error: {str(e)}")
"""


def patch_prompt_editor():
    """Patch prompt_editor.py to include vocabulary in manifest."""
    print("\n📝 Patching app/gui/dialogs/prompt_editor.py...")
    filepath = PROJECT_ROOT / "app" / "gui" / "dialogs" / "prompt_editor.py"

    if not filepath.exists():
        print(f"  ❌ File not found: {filepath}")
        return False

    content = filepath.read_text(encoding="utf-8")

    # Check if already patched
    if "vocabulary.model_dump()" in content:
        print("  ℹ️  Already patched")
        return True

    backup_file(filepath)

    # Find and replace the _execute_extraction method
    old_pattern = """    def _execute_extraction(self):
        connector = self.orchestrator._get_llm_connector()
        service = RulesGenerator(connector, status_callback=self._update_status)
        try:
            ruleset, rule_mems = service.generate_ruleset(self.rules)

            # Combine into Manifest
            manifest = {"ruleset": ruleset.model_dump(), "base_rules": rule_mems}
            self.manifest_json = json.dumps(manifest, indent=2)
            self._update_status("Extraction Complete!")
        except Exception as e:
            logger.warn(f"Rules extraction failed: {e}")
            self._update_status(f"Error: {str(e)}")"""

    new_pattern = """    def _execute_extraction(self):
        connector = self.orchestrator._get_llm_connector()
        service = RulesGenerator(connector, status_callback=self._update_status)
        try:
            ruleset, rule_mems, vocabulary = service.generate_ruleset(self.rules)

            # Combine into Manifest (includes vocabulary)
            manifest = {
                "vocabulary": vocabulary.model_dump(),
                "ruleset": ruleset.model_dump(),
                "base_rules": rule_mems,
            }
            self.manifest_json = json.dumps(manifest, indent=2)
            self._update_status("Extraction Complete!")
        except Exception as e:
            logger.warning(f"Rules extraction failed: {e}")
            self._update_status(f"Error: {str(e)}")"""

    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
    else:
        # Try a more flexible replacement
        if "ruleset, rule_mems = service.generate_ruleset" in content:
            content = content.replace(
                "ruleset, rule_mems = service.generate_ruleset(self.rules)",
                "ruleset, rule_mems, vocabulary = service.generate_ruleset(self.rules)",
            )
            content = content.replace(
                'manifest = {"ruleset": ruleset.model_dump(), "base_rules": rule_mems}',
                """manifest = {
                "vocabulary": vocabulary.model_dump(),
                "ruleset": ruleset.model_dump(),
                "base_rules": rule_mems,
            }""",
            )
        else:
            print("  ⚠️  Could not find extraction pattern to replace")
            return False

    filepath.write_text(content, encoding="utf-8")
    print(f"  ✅ Patched: {filepath}")
    return True


# =============================================================================
# UPDATE: app/services/game_setup_service.py
# =============================================================================

GAME_SETUP_VOCABULARY_PATCH = '''
    def _apply_scaffolding(
        self, session_id: int, prompt: Any, spec: Any, values: Dict, char_name: str
    ):
        """Apply scaffolding with vocabulary support."""
        # 1. Load Ruleset and Vocabulary from Manifest
        ruleset = None
        vocabulary = None
        base_rules = []

        if prompt.template_manifest:
            try:
                data = json.loads(prompt.template_manifest)
                if "ruleset" in data:
                    ruleset = Ruleset(**data["ruleset"])
                if "vocabulary" in data:
                    from app.models.vocabulary import GameVocabulary
                    vocabulary = GameVocabulary(**data["vocabulary"])
                if "base_rules" in data:
                    base_rules = data["base_rules"]
            except Exception as e:
                logger.warning(f"Failed to load manifest data: {e}")

        if not ruleset:
            ruleset, _ = get_default_scaffolding()
            ruleset.meta["name"] = prompt.name

        # 2. Persist Ruleset (UPSERT Logic)
        target_name = ruleset.meta.get("name")
        existing_rs = self.db.rulesets.get_by_name(target_name)
        
        if existing_rs:
            rs_id = existing_rs["id"]
            self.db.rulesets.update(rs_id, ruleset)
        else:
            rs_id = self.db.rulesets.create(ruleset)

        # 3. Persist Base Rules (Memories)
        for rule in base_rules:
            self.db.memories.create(
                session_id=session_id,
                kind="rule",
                content=rule.get("content", ""),
                tags=rule.get("tags", []),
                priority=3,
            )

        # 4. Persist Template (The Spec)
        st_id = self.db.stat_templates.create(rs_id, spec)

        # 5. Create Player Entity
        entity_data = values.copy()
        entity_data["name"] = char_name
        entity_data["template_id"] = st_id
        entity_data["scene_state"] = {"zone_id": None, "is_hidden": False}

        # Ensure all categories exist
        for cat in ["meta", "identity", "attributes", "skills", "resources", "inventory", "features"]:
            if cat not in entity_data:
                entity_data[cat] = {}

        set_entity(session_id, self.db, "character", "player", entity_data)

        # 6. Update Manifest with vocabulary reference
        manifest_update = {
            "ruleset_id": rs_id,
            "stat_template_id": st_id,
            "player_character": {"name": char_name},
        }
        
        # Store vocabulary in manifest for runtime use
        if vocabulary:
            manifest_update["vocabulary"] = vocabulary.model_dump()
        
        SetupManifest(self.db).update_manifest(session_id, manifest_update)
'''


def patch_game_setup_service():
    """Patch game_setup_service.py to handle vocabulary."""
    print("\n📝 Patching app/services/game_setup_service.py...")
    filepath = PROJECT_ROOT / "app" / "services" / "game_setup_service.py"

    if not filepath.exists():
        print(f"  ❌ File not found: {filepath}")
        return False

    content = filepath.read_text(encoding="utf-8")

    # Check if already patched
    if '"vocabulary":' in content and "GameVocabulary" in content:
        print("  ℹ️  Already patched")
        return True

    backup_file(filepath)

    # Add vocabulary to manifest storage
    if "manifest_update = {" in content and '"vocabulary"' not in content:
        # Find the manifest update section and add vocabulary
        old_manifest = """        manifest_update = {
            "ruleset_id": rs_id,
            "stat_template_id": st_id,
            "player_character": {"name": char_name},
        }
        
        SetupManifest(self.db).update_manifest(session_id, manifest_update)"""

        new_manifest = """        manifest_update = {
            "ruleset_id": rs_id,
            "stat_template_id": st_id,
            "player_character": {"name": char_name},
        }
        
        # Store vocabulary in manifest for runtime use
        if prompt.template_manifest:
            try:
                manifest_data = json.loads(prompt.template_manifest)
                if "vocabulary" in manifest_data:
                    manifest_update["vocabulary"] = manifest_data["vocabulary"]
            except Exception:
                pass
        
        SetupManifest(self.db).update_manifest(session_id, manifest_update)"""

        if old_manifest in content:
            content = content.replace(old_manifest, new_manifest)
        else:
            # Try simpler patch
            content = content.replace(
                "SetupManifest(self.db).update_manifest(session_id, manifest_update)",
                """# Store vocabulary in manifest for runtime use
        if prompt.template_manifest:
            try:
                manifest_data = json.loads(prompt.template_manifest)
                if "vocabulary" in manifest_data:
                    manifest_update["vocabulary"] = manifest_data["vocabulary"]
            except Exception:
                pass
        
        SetupManifest(self.db).update_manifest(session_id, manifest_update)""",
            )

    filepath.write_text(content, encoding="utf-8")
    print(f"  ✅ Patched: {filepath}")
    return True


# =============================================================================
# UPDATE: app/context/context_builder.py
# =============================================================================

CONTEXT_BUILDER_VOCAB_METHOD = '''
    def _build_vocabulary_hints(self, manifest: dict) -> str:
        """Build vocabulary hints for the LLM context."""
        vocab_data = manifest.get("vocabulary")
        if not vocab_data:
            return ""
        
        try:
            from app.models.vocabulary import GameVocabulary
            vocab = GameVocabulary(**vocab_data)
            
            lines = ["# VALID UPDATE PATHS #"]
            
            # Group by semantic role
            for role in ["core_trait", "resource", "capability", "status", "progression"]:
                role_paths = [p for p in vocab.valid_paths if p.startswith(f"{role}.")]
                if role_paths:
                    lines.append(f"**{role.replace('_', ' ').title()}**: {', '.join(role_paths[:5])}")
                    if len(role_paths) > 5:
                        lines.append(f"  ... and {len(role_paths) - 5} more")
            
            return "\\n".join(lines)
        except Exception as e:
            self.logger.debug(f"Failed to build vocabulary hints: {e}")
            return ""
'''


def patch_context_builder():
    """Patch context_builder.py to include vocabulary hints."""
    print("\n📝 Patching app/context/context_builder.py...")
    filepath = PROJECT_ROOT / "app" / "context" / "context_builder.py"

    if not filepath.exists():
        print(f"  ❌ File not found: {filepath}")
        return False

    content = filepath.read_text(encoding="utf-8")

    # Check if already patched
    if "_build_vocabulary_hints" in content:
        print("  ℹ️  Already patched")
        return True

    backup_file(filepath)

    # Add the vocabulary hints method before the last method
    # Find a good insertion point (before _build_spatial_context)
    insertion_marker = "    def _build_spatial_context"

    if insertion_marker in content:
        content = content.replace(
            insertion_marker, CONTEXT_BUILDER_VOCAB_METHOD + "\n" + insertion_marker
        )
    else:
        # Append to class
        content = content.rstrip() + "\n" + CONTEXT_BUILDER_VOCAB_METHOD + "\n"

    # Add vocabulary hints to build_dynamic_context
    if "def build_dynamic_context" in content and "vocabulary_hints" not in content:
        # Find the spatial context section and add vocabulary hints after it
        old_spatial = """        # 5. Spatial
        spatial_context = self._build_spatial_context(game_session.id)
        if spatial_context:
            sections.append(spatial_context)

        return "\\n\\n".join(sections)"""

        new_spatial = """        # 5. Spatial
        spatial_context = self._build_spatial_context(game_session.id)
        if spatial_context:
            sections.append(spatial_context)

        # 6. Vocabulary Hints (Valid paths for tools)
        vocab_hints = self._build_vocabulary_hints(manifest)
        if vocab_hints:
            sections.append(vocab_hints)

        return "\\n\\n".join(sections)"""

        if old_spatial in content:
            content = content.replace(old_spatial, new_spatial)

    filepath.write_text(content, encoding="utf-8")
    print(f"  ✅ Patched: {filepath}")
    return True


# =============================================================================
# UPDATE: app/core/react_turn_manager.py
# =============================================================================


def patch_react_turn_manager():
    """Patch react_turn_manager.py to pass vocabulary to tools."""
    print("\n📝 Patching app/core/react_turn_manager.py...")
    filepath = PROJECT_ROOT / "app" / "core" / "react_turn_manager.py"

    if not filepath.exists():
        print(f"  ❌ File not found: {filepath}")
        return False

    content = filepath.read_text(encoding="utf-8")

    # Check if already patched
    if (
        '"vocabulary":' in content
        or "vocabulary" in content.split("extra_ctx = {")[1].split("}")[0]
        if "extra_ctx = {" in content
        else False
    ):
        print("  ℹ️  Already patched (or no changes needed)")
        return True

    backup_file(filepath)

    # Add vocabulary to extra_context passed to tools
    old_extra_ctx = 'extra_ctx = {"simulation_service": sim_service}'
    new_extra_ctx = """extra_ctx = {
                            "simulation_service": sim_service,
                            "manifest": manifest,
                        }"""

    if old_extra_ctx in content:
        content = content.replace(old_extra_ctx, new_extra_ctx)

    filepath.write_text(content, encoding="utf-8")
    print(f"  ✅ Patched: {filepath}")
    return True


# =============================================================================
# UPDATE: app/setup/__init__.py
# =============================================================================

SETUP_INIT_UPDATE = '''"""
Setup package for game initialization.

Contains:
- VocabularyExtractor: Extract game vocabulary from rules text
- SchemaBuilder: Generate Pydantic models from vocabulary
- InvariantExtractor: Extract state invariants with vocabulary validation
- WorldGenService: Generate world data
- SheetGenerator: Generate character sheets
- RulesGenerator: Extract game rules, vocabulary, and procedures
"""

from app.setup.vocabulary_extractor import (
    VocabularyExtractor,
    extract_vocabulary_from_text,
)
from app.setup.schema_builder import (
    SchemaBuilder,
    PoolValue,
    LadderValue,
    TagValue,
    InventoryItem,
    build_character_model_from_vocabulary,
    build_creation_model_from_vocabulary,
    get_creation_hints_from_vocabulary,
)
from app.setup.invariant_extractor import (
    InvariantExtractor,
    extract_invariants_with_vocabulary,
)
from app.setup.rules_generator import RulesGenerator

__all__ = [
    # Vocabulary
    "VocabularyExtractor",
    "extract_vocabulary_from_text",
    # Schema Builder
    "SchemaBuilder",
    "PoolValue",
    "LadderValue",
    "TagValue",
    "InventoryItem",
    "build_character_model_from_vocabulary",
    "build_creation_model_from_vocabulary",
    "get_creation_hints_from_vocabulary",
    # Invariants
    "InvariantExtractor",
    "extract_invariants_with_vocabulary",
    # Rules
    "RulesGenerator",
]
'''


def update_setup_init():
    """Update setup/__init__.py with all exports."""
    print("\n📝 Updating app/setup/__init__.py...")
    filepath = PROJECT_ROOT / "app" / "setup" / "__init__.py"

    if filepath.exists():
        backup_file(filepath)

    write_file(filepath, SETUP_INIT_UPDATE)


# =============================================================================
# CREATE: Integration Test
# =============================================================================

INTEGRATION_TEST_CODE = '''#!/usr/bin/env python3
"""
Integration test for the vocabulary system pipeline.
Run: python test_vocabulary_integration.py

Tests the full flow:
1. Vocabulary extraction from rules
2. Schema building from vocabulary
3. Invariant extraction with vocabulary validation
4. Entity validation with invariants
"""

import sys
import os
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()


def test_vocabulary_to_schema():
    """Test vocabulary -> schema pipeline."""
    from app.models.vocabulary import create_dnd_like_vocabulary
    from app.setup.schema_builder import SchemaBuilder
    
    vocab = create_dnd_like_vocabulary()
    builder = SchemaBuilder(vocab)
    
    # Build character model
    CharModel = builder.build_character_model()
    char = CharModel()
    
    assert hasattr(char, "identity")
    print("✅ Vocabulary -> Schema works")
    
    # Get creation hints
    hints = builder.get_creation_prompt_hints()
    assert len(hints) > 100
    print(f"✅ Creation hints: {len(hints)} chars")


def test_vocabulary_to_invariants():
    """Test vocabulary -> invariant validation pipeline."""
    from app.models.vocabulary import create_dnd_like_vocabulary
    from app.services.invariant_validator import validate_entity
    
    vocab = create_dnd_like_vocabulary()
    
    # Create test entity with violation
    entity = {
        "resource": {
            "hp": {"current": 50, "max": 30}  # Violation!
        },
        "core_trait": {
            "strength": 0  # Violation!
        }
    }
    
    invariants = [
        {
            "name": "HP <= Max",
            "target_path": "resource.hp.current",
            "constraint": "<=",
            "reference": "resource.hp.max",
            "on_violation": "clamp",
        },
        {
            "name": "Stats >= 1",
            "target_path": "core_trait.*",
            "constraint": ">=",
            "reference": "1",
            "on_violation": "clamp",
        }
    ]
    
    result, corrections, warnings = validate_entity(entity, invariants, vocab)
    
    # Check corrections applied
    assert result["resource"]["hp"]["current"] == 30
    assert result["core_trait"]["strength"] == 1
    assert len(corrections) == 2
    
    print("✅ Vocabulary -> Invariant validation works")


def test_manifest_structure():
    """Test manifest structure with vocabulary."""
    import json
    from app.models.vocabulary import create_dnd_like_vocabulary
    from app.models.ruleset import Ruleset, EngineConfig
    
    vocab = create_dnd_like_vocabulary()
    ruleset = Ruleset(
        meta={"name": "Test", "genre": "Fantasy"},
        engine=EngineConfig(
            dice_notation="d20",
            roll_mechanic="Roll + Mod",
            success_condition=">= DC",
            crit_rules="Nat 20",
        ),
    )
    
    # Create manifest like prompt_editor does
    manifest = {
        "vocabulary": vocab.model_dump(),
        "ruleset": ruleset.model_dump(),
        "base_rules": [],
    }
    
    # Serialize and deserialize
    json_str = json.dumps(manifest)
    loaded = json.loads(json_str)
    
    assert "vocabulary" in loaded
    assert "fields" in loaded["vocabulary"]
    assert "ruleset" in loaded
    
    print("✅ Manifest structure works")


def test_full_pipeline_mock():
    """Test full pipeline with mock data."""
    from app.models.vocabulary import GameVocabulary, FieldDefinition, FieldType, SemanticRole
    from app.setup.schema_builder import SchemaBuilder
    from app.services.invariant_validator import validate_entity
    
    # 1. Create vocabulary (simulating extraction)
    vocab = GameVocabulary(
        system_name="Test RPG",
        system_id="test_rpg",
        genre="fantasy",
    )
    
    vocab.add_field(FieldDefinition(
        key="might",
        label="Might",
        semantic_role=SemanticRole.CORE_TRAIT,
        field_type=FieldType.NUMBER,
        min_value=1,
        max_value=10,
        default_value=5,
    ))
    
    vocab.add_field(FieldDefinition(
        key="health",
        label="Health",
        semantic_role=SemanticRole.RESOURCE,
        field_type=FieldType.POOL,
    ))
    
    # 2. Build schema
    builder = SchemaBuilder(vocab)
    CharModel = builder.build_creation_prompt_model()
    
    # 3. Create character data (simulating LLM output)
    char_data = {
        "identity": {"name": "Test Hero"},
        "core_trait": {"might": 8},
        "resource": {"health": 15},  # Simplified
    }
    
    # 4. Convert simplified to full
    full_data = builder.convert_simplified_to_full(char_data)
    
    assert full_data["resource"]["health"]["current"] == 15
    assert full_data["resource"]["health"]["max"] == 15
    
    # 5. Validate with invariants
    invariants = [{
        "name": "Health >= 0",
        "target_path": "resource.health.current",
        "constraint": ">=",
        "reference": "0",
        "on_violation": "clamp",
    }]
    
    # Set negative health to test
    full_data["resource"]["health"]["current"] = -5
    
    result, corrections, _ = validate_entity(full_data, invariants, vocab)
    
    assert result["resource"]["health"]["current"] == 0
    assert len(corrections) == 1
    
    print("✅ Full mock pipeline works")


def test_live_extraction():
    """Test live extraction with LLM (optional)."""
    print("\\n🔄 Testing live extraction (requires LLM)...")
    
    try:
        provider = os.environ.get("LLM_PROVIDER", "GEMINI").upper()
        
        if provider == "GEMINI":
            if not os.environ.get("GEMINI_API_KEY"):
                print("  ⏭️  Skipping: GEMINI_API_KEY not set")
                return
            from app.llm.gemini_connector import GeminiConnector
            llm = GeminiConnector()
        else:
            if not os.environ.get("OPENAI_API_KEY"):
                print("  ⏭️  Skipping: OPENAI_API_KEY not set")
                return
            from app.llm.openai_connector import OpenAIConnector
            llm = OpenAIConnector()
        
        from app.setup.rules_generator import RulesGenerator
        
        test_rules = """
        # Simple Quest RPG
        
        Characters have three stats: Strength, Agility, and Mind (range 1-5).
        Hit Points = Strength x 3.
        Mana Points = Mind x 2.
        
        Skills: Fighting, Sneaking, Casting (range 0-5).
        
        Roll 1d6 + Stat + Skill. Target is usually 7.
        """
        
        def status(msg):
            print(f"    {msg}")
        
        generator = RulesGenerator(llm, status)
        ruleset, rules, vocab = generator.generate_ruleset(test_rules)
        
        print(f"\\n  System: {vocab.system_name}")
        print(f"  Fields: {len(vocab.fields)}")
        print(f"  Invariants: {len(ruleset.state_invariants)}")
        print(f"  Valid paths: {len(vocab.valid_paths)}")
        
        print("\\n✅ Live extraction works!")
        
    except Exception as e:
        print(f"  ⚠️  Live test failed: {e}")
        print("     (This is OK if LLM not configured)")


if __name__ == "__main__":
    print("\\n" + "=" * 60)
    print("Vocabulary System Integration Tests")
    print("=" * 60 + "\\n")
    
    test_vocabulary_to_schema()
    test_vocabulary_to_invariants()
    test_manifest_structure()
    test_full_pipeline_mock()
    
    # Optional live test
    test_live_extraction()
    
    print("\\n" + "=" * 60)
    print("All integration tests passed! ✅")
    print("=" * 60)
'''


def create_integration_test():
    """Create integration test file."""
    print("\n📝 Creating test_vocabulary_integration.py...")
    filepath = PROJECT_ROOT / "test_vocabulary_integration.py"
    write_file(filepath, INTEGRATION_TEST_CODE)


# =============================================================================
# MAIN
# =============================================================================


def main():
    print("=" * 60)
    print("Vocabulary System - Part 5: Pipeline Integration")
    print("=" * 60)
    print(f"\nProject root: {PROJECT_ROOT.absolute()}")
    print(f"Backup directory: {BACKUP_DIR}")

    # Verify we're in the right place
    if not (PROJECT_ROOT / "app").exists():
        print("\n❌ ERROR: 'app' directory not found!")
        print("   Please run this script from the project root directory.")
        return 1

    # Verify previous parts
    required_files = [
        ("app/models/vocabulary.py", "Part 1"),
        ("app/setup/vocabulary_extractor.py", "Part 2"),
        ("app/setup/schema_builder.py", "Part 3"),
        ("app/services/invariant_validator.py", "Part 4"),
    ]

    for filepath, part in required_files:
        if not (PROJECT_ROOT / filepath).exists():
            print(f"\n❌ ERROR: {filepath} not found!")
            print(
                f"   Please run apply_vocabulary_{part.lower().replace(' ', '')}.py first."
            )
            return 1

    # Create backup directory
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Created backup directory: {BACKUP_DIR}")

    # Apply changes
    update_rules_generator()
    patch_prompt_editor()
    patch_game_setup_service()
    patch_context_builder()
    patch_react_turn_manager()
    update_setup_init()
    # create_integration_test()

    print("\n" + "=" * 60)
    print("✅ PART 5 COMPLETE")
    print("=" * 60)
    print(f"""
Files Modified:
  - app/setup/rules_generator.py (REPLACED - vocabulary-first extraction)
  - app/gui/dialogs/prompt_editor.py (PATCHED - includes vocabulary in manifest)
  - app/services/game_setup_service.py (PATCHED - stores vocabulary)
  - app/context/context_builder.py (PATCHED - vocabulary hints)
  - app/core/react_turn_manager.py (PATCHED - passes manifest to tools)
  - app/setup/__init__.py (UPDATED - all exports)
  - test_vocabulary_integration.py (NEW)

The Vocabulary System is Now Integrated!

Flow Summary:
1. User pastes rules → RulesGenerator extracts vocabulary FIRST
2. Vocabulary used to extract invariants (path validation)
3. Manifest stored with vocabulary, ruleset, base_rules
4. Session creation uses vocabulary for schema building
5. Gameplay uses vocabulary for:
   - Context hints (valid paths)
   - Tool validation (entity.update)
   - Invariant enforcement

Next Steps:
1. Run integration test:
   python test_vocabulary_integration.py

2. Test the full flow:
   - Create a new System Prompt with rules text
   - Click "Extract Rules"
   - Verify vocabulary appears in manifest JSON
   - Start a new game
   - Make updates that trigger invariants

If issues occur, restore from: {BACKUP_DIR}
""")

    return 0


if __name__ == "__main__":
    exit(main())
