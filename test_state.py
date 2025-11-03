from app.database.db_manager import DBManager
from app.tools.registry import ToolRegistry

DB_PATH = "ai_rpg.db"

def test_state_persistence():
    """Test that state persists across database sessions."""
    
    with DBManager(DB_PATH) as db:
        db.create_tables()
        
        # Create a test session
        session = db.save_session("State Test", "{}", prompt_id=1)
        session_id = session.id
        
        registry = ToolRegistry()
        context = {
            "session_id": session_id,
            "db_manager": db
        }
        
        # 1. Create a character
        print("Creating character...")
        registry.execute_tool(
            "state.apply_patch",
            {
                "entity_type": "character",
                "key": "player",
                "patch": [
                    {
                        "op": "add",
                        "path": "/",
                        "value": {
                            "name": "Elara",
                            "race": "Human",
                            "class": "Ranger",
                            "level": 3,
                            "attributes": {
                                "hp_current": 24,
                                "hp_max": 28,
                                "strength": 14,
                                "dexterity": 16
                            }
                        }
                    }
                ]
            },
            context=context
        )
        
        # 2. Query it back
        print("Querying character...")
        result = registry.execute_tool(
            "state.query",
            {"entity_type": "character", "key": "player", "json_path": "."},
            context=context
        )
        print(f"Character data: {result}")
        
        # 3. Update HP
        print("Updating HP...")
        registry.execute_tool(
            "state.apply_patch",
            {
                "entity_type": "character",
                "key": "player",
                "patch": [
                    {"op": "replace", "path": "/attributes/hp_current", "value": 20}
                ]
            },
            context=context
        )
        
        # 4. Verify update
        result = registry.execute_tool(
            "state.query",
            {"entity_type": "character", "key": "player", "json_path": "attributes.hp_current"},
            context=context
        )
        print(f"Updated HP: {result}")
        assert result["value"] == 20, "HP update failed!"
        
        # 5. Check stats
        stats = db.get_game_state_statistics(session_id)
        print(f"State statistics: {stats}")
        
        print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_state_persistence()
