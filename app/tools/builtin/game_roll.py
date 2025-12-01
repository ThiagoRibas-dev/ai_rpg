import random
import re
from typing import Any

_dice_re = re.compile(r"^\s*(\d+)\s*d\s*(\d+)\s*([+-]\s*\d+)?\s*$", re.I)


def handler(formula: str, reason: str = "Check", **context: Any) -> dict:
    """
    Rolls dice based on a formula (e.g. '1d20+5').
    """
    spec = formula
    if not spec:
        return {"error": "Missing dice specification."}

    m = _dice_re.match(spec.replace(" ", ""))
    # if not m: check if matches d[number], without the leading number of dice. If so, assume 1 die and re-match.
    if not m and spec.lower().startswith("d"):
        spec = "1" + spec
        m = _dice_re.match(spec.replace(" ", ""))

    # Once again check if we have a match, if not, we check if it matches just a number (e.g. '5'), and if so, assume it's 1d[number].
    if not m and re.match(r"^\s*\d+\s*$", spec):
        spec = f"1d{spec.strip()}"
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
        "formula": formula,
    }
