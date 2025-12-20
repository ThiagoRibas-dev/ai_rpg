import logging
from app.models.ruleset import Ruleset

logger = logging.getLogger(__name__)


def get_default_scaffolding():
    """
    Returns a default Ruleset and a placeholder for a sheet template (None).
    Legacy helper kept for compatibility with older tooling.
    """
    ruleset = Ruleset(
        meta={"name": "Simple RPG", "genre": "Fantasy"},
        engine={
            "dice_notation": "1d20",
            "roll_mechanic": "Roll + Stat",
            "success_condition": ">= 10",
            "crit_rules": "Nat 20",
        },
    )

    return ruleset, None
