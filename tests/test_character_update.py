import pytest
from app.tools.builtin.character_update import handler as character_update_handler
from app.models.entities import Character, CharacterAttributes
from app.models.property_definition import PropertyDefinition

# Mock DBManager and get_entity/set_entity for isolated testing
class MockDBManager:
    def __init__(self):
        self.entities = {}
        self.schema_extensions = {}

    def get_game_state_entity(self, session_id, entity_type, key):
        return self.entities.get((session_id, entity_type, key))

    def set_game_state_entity(self, session_id, entity_type, key, data):
        self.entities[(session_id, entity_type, key)] = data
        return 1 # Mock version

    def get_schema_extensions(self, session_id, entity_type):
        return self.schema_extensions.get((session_id, entity_type), {})

@pytest.fixture
def mock_db_manager():
    return MockDBManager()

@pytest.fixture
def session_id():
    return 123

@pytest.fixture
def initial_character_data():
    return Character(
        key="player",
        name="Hero",
        attributes=CharacterAttributes(hp_current=100, hp_max=100),
        conditions=[],
        location_key="town_square",
        inventory_key="player_inventory",
        properties={}
    ).model_dump()

@pytest.fixture
def setup_character(mock_db_manager, session_id, initial_character_data):
    mock_db_manager.set_game_state_entity(session_id, "character", "player", initial_character_data)

@pytest.fixture
def setup_schema_extensions(mock_db_manager, session_id):
    sanity_def = PropertyDefinition(
        name="Sanity",
        type="resource",
        description="Mental fortitude",
        default_value=100,
        has_max=True,
        min_value=0,
        max_value=100
    )
    alignment_def = PropertyDefinition(
        name="Alignment",
        type="enum",
        description="Moral alignment",
        default_value="Neutral",
        allowed_values=["Lawful Good", "Neutral", "Chaotic Evil"]
    )
    mock_db_manager.schema_extensions[(session_id, "character")] = {
        "Sanity": sanity_def.model_dump(),
        "Alignment": alignment_def.model_dump()
    }

def test_valid_core_attribute_update(mock_db_manager, session_id, setup_character):
    updates = [{"key": "hp_current", "value": 50}]
    result = character_update_handler(
        character_key="player",
        updates=updates,
        session_id=session_id,
        db_manager=mock_db_manager
    )
    assert result["success"] is True
    updated_char = Character(**mock_db_manager.get_game_state_entity(session_id, "character", "player"))
    assert updated_char.attributes.hp_current == 50

def test_valid_custom_property_update(mock_db_manager, session_id, setup_character, setup_schema_extensions):
    updates = [{"key": "Sanity", "value": 80}]
    result = character_update_handler(
        character_key="player",
        updates=updates,
        session_id=session_id,
        db_manager=mock_db_manager
    )
    assert result["success"] is True
    updated_char = Character(**mock_db_manager.get_game_state_entity(session_id, "character", "player"))
    assert updated_char.properties["Sanity"] == 80

def test_type_mismatch_fails_gracefully(mock_db_manager, session_id, setup_character, setup_schema_extensions):
    updates = [{"key": "Sanity", "value": "low"}] # Sanity is an integer
    with pytest.raises(ValueError, match="Property 'Sanity' must be of type 'resource', but received 'str'."):
        character_update_handler(
            character_key="player",
            updates=updates,
            session_id=session_id,
            db_manager=mock_db_manager
        )

def test_range_violation_fails_gracefully(mock_db_manager, session_id, setup_character, setup_schema_extensions):
    updates = [{"key": "Sanity", "value": 150}] # Max Sanity is 100
    with pytest.raises(ValueError, match="Property 'Sanity' cannot exceed 100. Received 150."):
        character_update_handler(
            character_key="player",
            updates=updates,
            session_id=session_id,
            db_manager=mock_db_manager
        )

def test_enum_violation_fails_gracefully(mock_db_manager, session_id, setup_character, setup_schema_extensions):
    updates = [{"key": "Alignment", "value": "Good"}] # Not in allowed values
    with pytest.raises(ValueError, match="Property 'Alignment' must be one of \\['Lawful Good', 'Neutral', 'Chaotic Evil'\\]. Received 'Good'."):
        character_update_handler(
            character_key="player",
            updates=updates,
            session_id=session_id,
            db_manager=mock_db_manager
        )

def test_death_logic_triggers_unconscious(mock_db_manager, session_id, initial_character_data):
    initial_character_data["attributes"]["hp_current"] = 10
    mock_db_manager.set_game_state_entity(session_id, "character", "player", initial_character_data)

    updates = [{"key": "hp_current", "value": 0}]
    character_update_handler(
        character_key="player",
        updates=updates,
        session_id=session_id,
        db_manager=mock_db_manager
    )
    updated_char = Character(**mock_db_manager.get_game_state_entity(session_id, "character", "player"))
    assert "unconscious" in updated_char.conditions
    assert "dead" not in updated_char.conditions

def test_death_logic_triggers_dead(mock_db_manager, session_id, initial_character_data):
    initial_character_data["attributes"]["hp_current"] = 10
    initial_character_data["attributes"]["hp_max"] = 10
    mock_db_manager.set_game_state_entity(session_id, "character", "player", initial_character_data)

    updates = [{"key": "hp_current", "value": -10}] # HP <= -HP_MAX
    character_update_handler(
        character_key="player",
        updates=updates,
        session_id=session_id,
        db_manager=mock_db_manager
    )
    updated_char = Character(**mock_db_manager.get_game_state_entity(session_id, "character", "player"))
    assert "unconscious" in updated_char.conditions
    assert "dead" in updated_char.conditions

def test_healing_removes_death_conditions(mock_db_manager, session_id, initial_character_data):
    initial_character_data["attributes"]["hp_current"] = 0
    initial_character_data["conditions"] = ["unconscious", "bleeding"]
    mock_db_manager.set_game_state_entity(session_id, "character", "player", initial_character_data)

    updates = [{"key": "hp_current", "value": 20}]
    character_update_handler(
        character_key="player",
        updates=updates,
        session_id=session_id,
        db_manager=mock_db_manager
    )
    updated_char = Character(**mock_db_manager.get_game_state_entity(session_id, "character", "player"))
    assert "unconscious" not in updated_char.conditions
    assert "dead" not in updated_char.conditions
    assert "bleeding" in updated_char.conditions # Other conditions remain

def test_undefined_custom_property_allowed_with_warning(mock_db_manager, session_id, setup_character):
    updates = [{"key": "NewStat", "value": 5}]
    result = character_update_handler(
        character_key="player",
        updates=updates,
        session_id=session_id,
        db_manager=mock_db_manager
    )
    assert result["success"] is True
    updated_char = Character(**mock_db_manager.get_game_state_entity(session_id, "character", "player"))
    assert updated_char.properties["NewStat"] == 5
    # Check for warning in logs (requires more advanced mocking or log capturing)

def test_multiple_updates_in_one_call(mock_db_manager, session_id, setup_character, setup_schema_extensions):
    updates = [
        {"key": "hp_current", "value": 75},
        {"key": "Sanity", "value": 60},
        {"key": "Alignment", "value": "Chaotic Evil"}
    ]
    result = character_update_handler(
        character_key="player",
        updates=updates,
        session_id=session_id,
        db_manager=mock_db_manager
    )
    assert result["success"] is True
    updated_char = Character(**mock_db_manager.get_game_state_entity(session_id, "character", "player"))
    assert updated_char.attributes.hp_current == 75
    assert updated_char.properties["Sanity"] == 60
    assert updated_char.properties["Alignment"] == "Chaotic Evil"
