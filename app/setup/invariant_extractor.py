"""
Invariant Extractor
===================
Vocabulary-aware extraction using Forked Context.
Updated: Fail-fast architecture.
"""

import logging
from typing import List, Optional, Callable, Union

from pydantic import BaseModel

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.vocabulary import GameVocabulary
from app.models.ruleset import StateInvariant
from app.prompts.templates import EXTRACT_INVARIANTS_INSTRUCTION

logger = logging.getLogger(__name__)

class ExtractedInvariant(BaseModel):
    name: str
    target_path: str
    constraint: str
    reference: str
    on_violation: str
    correction_value: Optional[str] = None

class InvariantList(BaseModel):
    invariants: List[ExtractedInvariant]

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
    
    def extract(self, rules_source: Union[str, List[Message]]) -> List[StateInvariant]:
        # 1. Build Base Context
        if isinstance(rules_source, list):
            base_history = list(rules_source)
        else:
            base_history = [
                Message(role="system", content="You are a TTRPG Analyst."),
                Message(role="user", content=f"# RULES TEXT\n\n{rules_source}")
            ]

        # 2. Build Instruction
        path_examples = []
        seen_cats = set()
        for path in self.vocab.valid_paths[:50]:  
            parts = path.split(".")
            if parts[0] not in seen_cats:
                seen_cats.add(parts[0])
                path_examples.append(f"\n  **{parts[0]}**:")
            path_examples.append(f"    - `{path}`")
        
        paths_text = "".join(path_examples)
        instruction = EXTRACT_INVARIANTS_INSTRUCTION.format(paths_text=paths_text)
        
        # 3. Extract (Fail Fast)
        history = base_history + [Message(role="user", content=instruction)]
        
        result = self.llm.get_structured_response(
            system_prompt="IGNORED",
            chat_history=history,
            output_schema=InvariantList,
            temperature=0.2,
        )
        
        # 4. Validate
        valid_invariants = []
        for inv in result.invariants:
            if not self.vocab.validate_path(inv.target_path):
                continue
            
            valid_invariants.append(StateInvariant(
                name=inv.name,
                target_path=inv.target_path,
                constraint=inv.constraint,
                reference=inv.reference,
                on_violation=inv.on_violation,
                correction_value=inv.correction_value,
            ))
        
        return valid_invariants

def extract_invariants_with_vocabulary(
    llm: LLMConnector,
    vocabulary: GameVocabulary,
    rules_text: str,
    status_callback: Optional[Callable[[str], None]] = None,
) -> List[StateInvariant]:
    extractor = InvariantExtractor(llm, vocabulary, status_callback)
    return extractor.extract(rules_text)
