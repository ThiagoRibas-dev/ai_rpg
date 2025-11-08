import random
import re

_dice_re = re.compile(r"^\s*(\d+)\s*d\s*(\d+)\s*([+-]\s*\d+)?\s*$", re.I)


def handler(dice: str | None = None, dice_spec: str | None = None, **context) -> dict:
    spec = dice or dice_spec
    if not spec:
        raise ValueError("Missing dice specification.")
    m = _dice_re.match(spec.replace(" ", ""))
    if not m:
        raise ValueError(f"Invalid dice specification: {spec}")
    n, sides, mod = int(m.group(1)), int(m.group(2)), m.group(3)
    rolls = [random.randint(1, sides) for _ in range(n)]
    modifier = int(mod.replace(" ", "")) if mod else 0
    total = sum(rolls) + modifier
    return {"total": total, "rolls": rolls, "modifier": modifier}
