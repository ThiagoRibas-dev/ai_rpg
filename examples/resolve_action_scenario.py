import sys
import os
from pprint import pprint

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.tools.registry import ToolRegistry

def main():
    """
    Demonstrates the 'on-the-fly' rule generation by invoking the 
    rules.resolve_action tool with a dynamically created policy.
    """
    # The ToolRegistry will automatically discover our new tool
    registry = ToolRegistry()

    # 1. The LLM narrates the scene and internally decides on a rule.
    # LLM Narrative: "The ancient door is sealed by a strange, humming lock..."
    # LLM Internal Thought: "This is a 'Techno-Mancy' check. DC 18. 
    #                      It uses Tech skill, with a bonus for Magic items."

    # 2. The LLM constructs the entire resolution policy object.
    action_id = "Open Humming Lock"
    actor_id = "player1"
    
    resolution_policy = {
        "type": "skill_check",
        "dc": 18,
        "base_formula": "1d20",
        "modifiers": [
            {"source": "Player's Tech Skill", "value": 4},
            {"source": "Equipped 'Arcane Lenses' (Magic Item)", "value": 2},
            {"source": "Distracting humming sound", "value": -1}
        ]
    }

    # 3. The LLM calls the tool with the policy it just invented.
    tool_args = {
        "action_id": action_id,
        "actor_id": actor_id,
        "resolution_policy": resolution_policy
    }

    print("--- LLM Tool Call ---")
    pprint(tool_args)
    
    # 4. The tool executes the policy and returns the deterministic result.
    result = registry.execute_tool("rules.resolve_action", tool_args)

    print("\n--- Tool Result ---")
    pprint(result)

if __name__ == "__main__":
    main()