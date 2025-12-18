
import random
import re
from typing import Any

_dice_re = re.compile(r"^\s*(\d+)\s*d\s*(\d+)\s*([+-]\s*\d+)?\s*$", re.I)

def handler(formula: str, reason: str = "Action", **context: Any) -> dict:
    """
    Rolls dice based on a formula (e.g. '1d20+5').
    """
    spec = formula.strip()
    if not spec:
        return {"error": "Missing dice specification."}

    # Normalize "d20" to "1d20"
    if spec.lower().startswith("d"):
        spec = "1" + spec
    
    # Normalize "5" to "1d5" (edge case)
    if re.match(r"^\d+$", spec):
        spec = f"1d{spec}"

    m = _dice_re.match(spec.replace(" ", ""))
    if not m:
        return {"error": f"Invalid dice formula: {formula}"}

    n = int(m.group(1))
    sides = int(m.group(2))
    mod_str = m.group(3)
    
    rolls = [random.randint(1, sides) for _ in range(n)]
    modifier = int(mod_str.replace(" ", "")) if mod_str else 0
    total = sum(rolls) + modifier

    return {
        "outcome": f"Rolled {total} ({reason})",
        "formula": formula,
        "rolls": rolls,
        "modifier": modifier,
        "total": total,
        "reason": reason
    }
