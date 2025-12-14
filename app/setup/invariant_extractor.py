"""
Invariant Extractor
===================
Vocabulary-aware extraction of state invariants from rules text.
"""

import logging
from typing import List, Optional, Callable

from pydantic import BaseModel, Field

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.vocabulary import GameVocabulary
from app.models.ruleset import StateInvariant

logger = logging.getLogger(__name__)


# =============================================================================
# EXTRACTION SCHEMAS
# =============================================================================

class ExtractedInvariant(BaseModel):
    name: str = Field(..., description="Human-readable name")
    target_path: str = Field(..., description="Path to constrained value")
    constraint: str = Field(..., description="Comparison: >=, <=, ==, !=, in_range")
    reference: str = Field(..., description="Value or path to compare against")
    on_violation: str = Field("clamp", description="Action: clamp, flag, reject")
    correction_value: Optional[str] = Field(None, description="Correction value if clamping")


class InvariantList(BaseModel):
    invariants: List[ExtractedInvariant] = Field(default_factory=list)


# =============================================================================
# EXTRACTION PROMPT
# =============================================================================

def build_invariant_extraction_prompt(vocab: GameVocabulary) -> str:
    """
    Build a vocabulary-aware extraction prompt.
    Includes valid paths so the LLM knows exactly what it can reference.
    """
    # Get sample paths grouped by category (first part of path)
    path_examples = []
    seen_cats = set()
    
    # vocab.valid_paths now returns canonical paths (e.g. resources.hp.current)
    for path in vocab.valid_paths[:40]:  
        parts = path.split(".")
        if parts[0] not in seen_cats:
            seen_cats.add(parts[0])
            path_examples.append(f"\n  **{parts[0]}**:")
        path_examples.append(f"    - `{path}`")
    
    paths_text = "".join(path_examples)
    
    return f"""
You are extracting STATE INVARIANTS from game rules — conditions that must ALWAYS be true.

## VALID PATHS FOR THIS SYSTEM

You may ONLY use paths that match this vocabulary:
{paths_text}

For wildcards, use patterns like:
- `attributes.*` — all core attributes
- `resources.*.current` — current value of all resources
- `skills.*` — all skills

## CONSTRAINT TYPES

| Constraint | Meaning | Example |
|------------|---------|---------|
| `>=` | Must be greater than or equal | HP >= 0 |
| `<=` | Must be less than or equal | HP <= max HP |
| `==` | Must equal | (rare) |
| `!=` | Must not equal | (rare) |
| `in_range` | Must be within range | Stats in 1-20 |

## REFERENCE VALUES

References can be:
- **Literal numbers**: `"0"`, `"-10"`, `"100"`
- **Paths**: `"resources.hp.max"`, `"attributes.strength"`
- **Expressions**: `"progression.level + 3"`, `"(attributes.constitution - 10) // 2"`

## VIOLATION ACTIONS

| Action | Behavior |
|--------|----------|
| `clamp` | Auto-correct to boundary value |
| `flag` | Warn but allow |
| `reject` | Block the operation |

## EXAMPLES

```json
{{
  "name": "HP cannot exceed maximum",
  "target_path": "resources.hp.current",
  "constraint": "<=",
  "reference": "resources.hp.max",
  "on_violation": "clamp",
  "correction_value": "resources.hp.max"
}}
```

```json
{{
  "name": "Attributes minimum",
  "target_path": "attributes.*",
  "constraint": ">=",
  "reference": "1",
  "on_violation": "clamp",
  "correction_value": "1"
}}
```

Extract 5-15 invariants appropriate for this game system.
Focus on:
- Resource bounds (HP, mana, stress)
- Stat limits (min/max values)
- Derived constraints (current <= max)
"""


# =============================================================================
# INVARIANT EXTRACTOR
# =============================================================================

class InvariantExtractor:
    def __init__(
        self,
        llm: LLMConnector,
        vocabulary: GameVocabulary,
        status_callback: Optional[Callable[[str], None]] = None,
    ):
        self.llm = llm
        self.vocab = vocabulary
        self.status_callback = status_callback
    
    def _update_status(self, message: str):
        if self.status_callback:
            self.status_callback(message)
        logger.info(f"[InvariantExtractor] {message}")
    
    def extract(self, rules_text: str) -> List[StateInvariant]:
        self._update_status("Building extraction prompt...")
        prompt = build_invariant_extraction_prompt(self.vocab)
        
        self._update_status("Extracting invariants...")
        
        max_len = 6000
        if len(rules_text) > max_len:
            rules_text = rules_text[:max_len] + "\n[truncated]"
        
        try:
            result = self.llm.get_structured_response(
                system_prompt=prompt,
                chat_history=[
                    Message(role="user", content=f"# RULES TEXT\n\n{rules_text}")
                ],
                output_schema=InvariantList,
                temperature=0.3,
            )
        except Exception as e:
            logger.error(f"Invariant extraction failed: {e}")
            return self._get_default_invariants()
        
        self._update_status("Validating invariants...")
        valid_invariants = []
        
        for inv in result.invariants:
            if not self.vocab.validate_path(inv.target_path):
                logger.warning(f"Skipping invariant with invalid path: {inv.target_path}")
                continue
            
            ref = inv.reference
            # Simple check if ref is a path
            if ref and "." in ref and not any(op in ref for op in ["+", "-", "*", "/"]):
                if not self.vocab.validate_path(ref):
                    logger.warning(f"Skipping invariant with invalid reference path: {ref}")
                    continue
            
            valid_invariants.append(StateInvariant(
                name=inv.name,
                target_path=inv.target_path,
                constraint=inv.constraint,
                reference=inv.reference,
                on_violation=inv.on_violation,
                correction_value=inv.correction_value,
            ))
        
        self._update_status(f"Extracted {len(valid_invariants)} valid invariants")
        return valid_invariants
    
    def _get_default_invariants(self) -> List[StateInvariant]:
        defaults = []
        for path in self.vocab.valid_paths:
            if "resources." in path and path.endswith(".current"):
                max_path = path.replace(".current", ".max")
                if max_path in self.vocab.valid_paths:
                    base_name = path.split(".")[1]
                    defaults.append(StateInvariant(
                        name=f"{base_name.title()} cannot exceed max",
                        target_path=path,
                        constraint="<=",
                        reference=max_path,
                        on_violation="clamp",
                        correction_value=max_path,
                    ))
        return defaults


def extract_invariants_with_vocabulary(
    llm: LLMConnector,
    vocabulary: GameVocabulary,
    rules_text: str,
    status_callback: Optional[Callable[[str], None]] = None,
) -> List[StateInvariant]:
    extractor = InvariantExtractor(llm, vocabulary, status_callback)
    return extractor.extract(rules_text)
