import random

# 1. Define the JSON schema for the tool
schema = {
    "name": "rng.roll",
    "description": "Rolls dice based on a dice specification (e.g., '1d20', '2d6+3').",
    "parameters": {
        "type": "object",
        "properties": {
            "dice_spec": {
                "type": "string",
                "description": "The dice specification string (e.g., '1d20', '2d6+3')."
            }
        },
        "required": ["dice_spec"]
    }
}

# 2. Implement the handler function
def handler(dice_spec: str) -> int:
    """
    Rolls dice based on a dice specification string.
    
    For simplicity, this initial implementation only handles a single die roll.
    A more robust implementation would parse the full dice notation.
    """
    try:
        if 'd' in dice_spec:
            num_dice, die_type = map(int, dice_spec.split('d'))
            return sum(random.randint(1, die_type) for _ in range(num_dice))
        else:
            return random.randint(1, int(dice_spec))
    except Exception:
        raise ValueError(f"Invalid dice specification: {dice_spec}")
