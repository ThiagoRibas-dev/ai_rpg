from typing import Dict, Any

def handler(**context: Any) -> Dict[str, Any]:
    """
    A simple flag tool that signals the end of the Session Zero setup phase.
    The orchestrator listens for this result to transition the game mode.

    Args:
        context (Any): The tool execution context.

    Returns:
        Dict[str, Any]: A dictionary indicating that setup is complete.
    """
    return {"setup_complete": True}
