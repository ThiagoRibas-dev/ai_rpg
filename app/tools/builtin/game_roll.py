import random
import re
from typing import Any

_dice_re = re.compile(r"^\s*(\d+)\s*d\s*(\d+)\s*([+-]\s*\d+)?\s*$", re.I)

def handler(
    formula: str,
    reason: str = "Check",
    **context: Any
) -> dict:
    """
    Rolls dice based on a formula (e.g. '1d20+5').
    """
    # Logic inlined from rng_roll.py
    spec = formula
    if not spec:
        return {"error": "Missing dice specification."}
    
    m = _dice_re.match(spec.replace(" ", ""))
    if not m:
        return {"error": f"Invalid dice specification: {spec}"}
    
    n, sides, mod = int(m.group(1)), int(m.group(2)), m.group(3)
    rolls = [random.randint(1, sides) for _ in range(n)]
    modifier = int(mod.replace(" ", "")) if mod else 0
    total = sum(rolls) + modifier
    
    # Enhance result for Chat History context
    return {
        "outcome": f"Rolled {total} ({reason})",
        "total": total,
        "rolls": rolls,
        "formula": formula
    }
