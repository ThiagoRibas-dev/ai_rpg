import random
import re
from typing import Any

# Match: 1d20, 2d6, 4d6dl1, 1d6!, 2d20kh1+5, etc.
# Groups: (n_dice), (sides), (exploding), (keep_drop_type), (keep_drop_count), (modifier)
_dice_re = re.compile(r"^\s*(\d+)\s*[dD]\s*(\d+)(!)?(?:([kKdD][hHlL])(\d+))?\s*([+-]\s*\d+)?\s*$")

def handler(formula: str, reason: str = "Action", **context: Any) -> dict:
    """
    Rolls dice based on an advanced formula (e.g. '1d20+5', '2d20kh1', '4d6dl1', '1d6!').
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
    exploding = bool(m.group(3))
    kd_type = m.group(4).lower() if m.group(4) else None
    kd_count = int(m.group(5)) if m.group(5) else 0
    mod_str = m.group(6)

    rolls = []
    # Roll dice, including exploding logic
    for _ in range(n):
        roll = random.randint(1, sides)
        rolls.append(roll)
        while exploding and roll == sides:
            roll = random.randint(1, sides)
            rolls.append(roll)

    # Keep/Drop logic
    active_rolls = rolls.copy()
    if kd_type and kd_count > 0:
        sorted_rolls = sorted(active_rolls, reverse=True)
        if kd_type == 'kh':
            active_rolls = sorted_rolls[:kd_count]
        elif kd_type == 'kl':
            active_rolls = sorted_rolls[-kd_count:]
        elif kd_type == 'dh':
            active_rolls = sorted_rolls[kd_count:]
        elif kd_type == 'dl':
            active_rolls = sorted_rolls[:-kd_count]

    modifier = int(mod_str.replace(" ", "")) if mod_str else 0
    total = sum(active_rolls) + modifier

    return {
        "outcome": f"Rolled {total} ({reason})",
        "formula": formula,
        "rolls": rolls,
        "active_rolls": active_rolls,
        "modifier": modifier,
        "total": total,
        "reason": reason
    }
