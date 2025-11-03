import os
import json
import logging
from typing import Callable, Dict, Any, List
from datetime import datetime
from app.gui.main_view import MainView
from app.models.session import Session
from app.models.game_session import GameSession
from app.llm.llm_connector import LLMConnector
from app.llm.gemini_connector import GeminiConnector
from app.llm.openai_connector import OpenAIConnector
from app.tools.registry import ToolRegistry
from app.io.schemas import TurnPlan, NarrativeStep, ActionChoices
from app.models.message import Message
from app.core.vector_store import VectorStore

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 20
TOOL_BUDGET = 4

PLAN_TEMPLATE = """
{identity}

# PLANNING STEP
Your goal is to select and execute the most appropriate tools to respond to the user's input and advance the game state.

CHECKLIST (answer briefly before any tool calls):
- Is the player’s requested action possible right now? If trivial, describe outcome and avoid tools.
- If uncertain about facts, call state.query first.
- If mechanics apply, state DC rationale and which rolls are needed.
- Specify exactly which tools you’ll call and why (max {tool_budget}).
- Specify intended state/memory changes.

MEMORY MANAGEMENT GUIDELINES:
- Before making important decisions, use memory.query to check if you have relevant past information
- Create memories (memory.upsert) for:
  * Episodic: Important story events, character actions, plot developments
  * Semantic: Facts about the world, rules, mechanics that were learned
  * Lore: Background information, history, world-building details
  * User Pref: Player preferences for gameplay, style, or story direction
- Update memories (memory.update) when information changes or priorities shift
- Delete memories (memory.delete) only if they're truly incorrect or obsolete
- Use priority levels wisely: 5 = critical, always relevant; 3 = normal; 1 = minor detail
- Tag memories with relevant keywords for easier retrieval

Available tools (JSON Schemas):
{tool_schemas}
"""

NARRATIVE_TEMPLATE = """
{identity}

# Narrative Step

Write the next scene based on the Planner's Intent and the tool results.
Return a JSON object strictly matching the NarrativeStep schema.

The Planner's Intent (your high-level goal for this turn):
{planner_thought}

MEMORY NOTES:
- Memories shown in context were automatically retrieved and have been marked as accessed
- You don't need to create memory.upsert calls in tool results - those are handled by the Planner
- Focus on using the retrieved memories to inform your narrative

TURN METADATA INSTRUCTIONS:
- After writing your narrative, also provide:
  * turn_summary: A one-sentence summary of what happened this turn
  * turn_tags: 3-5 tags categorizing this turn (e.g., 'combat', 'dialogue', 'discovery', 'travel')
  * turn_importance: Rate 1-5 how important this turn is to the overall story
    - 1 = Minor detail, small talk
    - 3 = Normal gameplay, advancing the scene
    - 5 = Critical plot point, major revelation, dramatic turning point

Guidelines:
- Your narration must align with the Planner's Intent.
- Use second person ("You ...").
- Respect tool outcomes; do not fabricate mechanics. If tool results are empty, rely primarily on the Planner's Intent.
- Consistency checks: do not contradict state.query results. If you detect an inconsistency, propose a minimal patch.

Tool results:
{tool_results}
"""

CHOICE_GENERATION_TEMPLATE = """Based on the current game state and the narrative you just presented, generate between 3 and 5 concise action choices written from the Player's own perspective.

Each choice should be:
- A short, actionable statement (preferably under 10 words)
- Something the player can say or do
- Relevant to the current situation
- Distinct from the other choices

Guidelines:
- Think about what makes sense given the narrative context
- Offer diverse options (e.g., combat, diplomacy, investigation)
- Keep choices clear and direct

Recent narrative context:
{narrative}
"""

class Orchestrator:
    def __init__(self, view: MainView, db_manager):
        self.view = view
        self.db_manager = db_manager
        self.tool_event_callback: Callable[[str], None] | None = None
        self.llm_connector = self._get_llm_connector()
        self.tool_registry = ToolRegistry()
        self.vector_store = VectorStore()  # 🆕 Initialize vector store
        self._indexed_world_prompts: set[int] = set()
        self.view.orchestrator = self
        self.session: Session | None = None
        self.view.memory_inspector.orchestrator = self

    def _get_llm_connector(self) -> LLMConnector:
        provider = os.environ.get("LLM_PROVIDER", "GEMINI").upper()
        if provider == "GEMINI":
            return GeminiConnector()
        elif provider == "OPENAI":
            return OpenAIConnector()
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

    def _get_truncated_history(self) -> List[Message]:
        """
        Returns a truncated copy of the session history, preserving the system prompt.
        """
        if not self.session:
            return []
        
        full_history = self.session.get_history()
        if len(full_history) <= MAX_HISTORY_MESSAGES:
            return full_history

        # Preserve the first message (system prompt) and take the last X messages.
        system_prompt = full_history[0]
        recent_messages = full_history[-(MAX_HISTORY_MESSAGES - 1):]
        
        return [system_prompt] + recent_messages

    def _extract_keywords(self, text: str, min_length: int = 3) -> List[str]:
        """
        Simple keyword extraction from text.
        Returns words longer than min_length, lowercased, without punctuation.
        """
        import re
        # Remove punctuation and split into words
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter by length and remove common stop words
        stop_words = {'the', 'and', 'but', 'for', 'not', 'with', 'this', 'that', 'from', 'have', 'been', 'are', 'was', 'were'}
        keywords = [w for w in words if len(w) >= min_length and w not in stop_words]
        return list(set(keywords))  # Remove duplicates

    def _get_relevant_memories(self, session: GameSession, recent_messages: List[Message], limit: int = 10) -> List[Any]:
        """
        Retrieve relevant memories for the current context.
        Combines keyword matching with priority weighting.
        """
        if not session.id:
            return []
        
        # Extract keywords from recent messages
        recent_text = " ".join([msg.content for msg in recent_messages[-5:]])
        keywords = self._extract_keywords(recent_text)
        
        # Get all memories for this session
        all_memories = self.db_manager.get_memories_by_session(session.id)
        
        if not all_memories:
            return []
        
        # Semantic top-k (blend with keyword/priority)
        semantic_hits = []
        try:
            semantic_hits = self.vector_store.search_memories(session.id, recent_text, k=min(12, limit * 2), min_priority=1)
        except Exception:
            semantic_hits = []
        hit_ids = {h["memory_id"] for h in semantic_hits}

        # Score each memory (existing SQL list)
        scored_memories = []
        for mem in all_memories:
            score = 0
            
            # Priority 5 memories always get a high base score
            if mem.priority == 5:
                score += 100
            elif mem.priority == 4:
                score += 50
            elif mem.priority == 3:
                score += 20
            
            # Keyword matching
            mem_text = (mem.content + " " + " ".join(mem.tags_list())).lower()
            keyword_matches = sum(1 for kw in keywords if kw in mem_text)
            score += keyword_matches * 10
            
            # Recency bias (newer memories get small boost)
            try:
                created = datetime.fromisoformat(mem.created_at)
                age_days = (datetime.now() - created).days
                recency_score = max(0, 10 - age_days)  # Up to 10 points for very recent
                score += recency_score
            except (ValueError, AttributeError):
                pass
            
            # Boost if semantic match
            if mem.id in hit_ids:
                score += 50
            scored_memories.append((score, mem))
        
        # Sort by score and take top N
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        top_memories = [mem for score, mem in scored_memories[:limit] if score > 0]
        
        # Update access tracking for retrieved memories
        for mem in top_memories:
            self.db_manager.update_memory_access(mem.id)
        
        return top_memories

    def _format_memories_for_context(self, memories: List[Any]) -> str:
        """
        Format memories for inclusion in the system prompt.
        """
        if not memories:
            return ""
        
        lines = ["# RELEVANT MEMORIES #"]
        
        kind_emoji = {
            "episodic": "📖",
            "semantic": "💡",
            "lore": "📜",
            "user_pref": "⚙️"
        }
        
        for mem in memories:
            emoji = kind_emoji.get(mem.kind, "📝")
            priority_stars = "★" * mem.priority
            tags_str = f" [{', '.join(mem.tags_list())}]" if mem.tags_list() else ""
            
            lines.append(
                f"{emoji} [{mem.kind.title()}] (Priority: {priority_stars}, ID: {mem.id}){tags_str}\n"
                f"   {mem.content}"
            )
        
        lines.append("")  # Empty line after memories
        return "\n".join(lines)

    def _assemble_context(self, base_template: str, session: GameSession) -> str:
        """
        Assembles the final system prompt by combining Memory, Memories, Turn Metadata, 
        World Info, base template, and Author's Note.
        """
        parts = []

        # 1. Base template
        parts.append(f"### INSTRUCTIONS\n{base_template}\n\n")

        # 2. Memory (persistent high-level context)
        if session.memory and session.memory.strip():
            parts.append(f"### MEMORIES\n{session.memory.strip()}\n")

        # 3. Relevant Memories (AI-managed knowledge base)
        recent_history = self._get_truncated_history()
        relevant_memories = self._get_relevant_memories(session, recent_history, limit=10)
        if relevant_memories:
            memories_section = self._format_memories_for_context(relevant_memories)
            parts.append(memories_section)

        # 4. Relevant Turn Metadata (semantic search of past events)
        if session.id:
            recent_text = " ".join([msg.content for msg in recent_history[-5:]])
            relevant_turns = self.vector_store.search_relevant_turns(
                session_id=session.id,
                query_text=recent_text,
                top_k=5,
                min_importance=3  # Only include important turns
            )
            if relevant_turns:
                turn_metadata_section = self._format_turn_metadata_for_context(relevant_turns)
                parts.append(turn_metadata_section)

        # 5. World Info (semantic RAG, lazy indexing)
        if session.prompt_id:
            try:
                if session.prompt_id not in self._indexed_world_prompts:
                    # Index all WI for this prompt once
                    for wi in self.db_manager.get_world_info_by_prompt(session.prompt_id):
                        self.vector_store.upsert_world_info(session.prompt_id, wi.id, wi.content)
                    self._indexed_world_prompts.add(session.prompt_id)
                recent_text = " ".join([msg.content for msg in recent_history[-5:]])
                wi_hits = self.vector_store.search_world_info(session.prompt_id, recent_text, k=4)
                if wi_hits:
                    parts.append("### WORLD INFO\n" + "\n\n".join([h["text"] for h in wi_hits]) + "\n")
            except Exception:
                pass

        # 6. Author's Note
        if session.authors_note and session.authors_note.strip():
            parts.append(f"### AUTHOR'S NOTE\n{session.authors_note.strip()}\n")

        return "\n".join(parts)

    def plan_and_execute(self, session: GameSession):
        logger.debug("Starting plan_and_execute")
        user_input = self.view.get_input()
        if not user_input or not self.session:
            logger.debug("No user input or session found, returning.")
            return

        self.session.add_message("user", user_input)
        self.view.add_message_bubble("user", user_input)
        self.view.clear_input()

        # 1) Plan
        try:
            chat_history = self._get_truncated_history()

            import json as _json
            base_plan_template = PLAN_TEMPLATE.format(
                identity=chat_history[0].content,
                tool_schemas=_json.dumps(self.tool_registry.get_all_schemas(), indent=2),
                tool_budget=TOOL_BUDGET,
            )
            system_prompt_plan = self._assemble_context(base_plan_template, session)
            
            plan_dict = self.llm_connector.get_structured_response(
                system_prompt=system_prompt_plan,
                chat_history=chat_history,
                output_schema=TurnPlan
            )
            if plan_dict is None: # Add this check
                logger.error("LLM returned no structured response for TurnPlan.")
                self.view.add_message_bubble("system", "Error: AI failed to generate a valid plan.")
                return
            plan = TurnPlan.model_validate(plan_dict)
            self.view.add_thought_bubble(plan.thought)  # Use thought bubble
        except Exception as e:
            logger.error(f"Error during planning: {e}", exc_info=True)
            self.view.add_message_bubble("system", f"Error during planning: {e}")
            return

        # 2) Execute tools (enforce a small budget)
        tool_results: List[Dict[str, Any]] = []
        if plan.tool_calls:
            for call in plan.tool_calls[:TOOL_BUDGET]:
                try:
                    tool_name = call.name
                    tool_args_str = call.arguments or "{}"
                    tool_args = json.loads(tool_args_str)
                    
                    # Add to tool calls panel
                    self.view.add_tool_call(tool_name, tool_args)
                    
                    # Pass context to tools that need it
                    context = {
                        "session_id": session.id,
                        "db_manager": self.db_manager,
                        "current_game_time": getattr(session, "game_time", None),
                        "vector_store": self.vector_store,
                    }
                    
                    result = self.tool_registry.execute_tool(tool_name, tool_args, context=context)
                    tool_results.append({"tool_name": tool_name, "arguments": tool_args, "result": result})
                    
                    # Add result to tool calls panel
                    self.view.add_tool_result(result, is_error=False)
                    # Persist game time updates (time.advance)
                    if tool_name == "time.advance" and isinstance(result, dict) and "new_time" in result:
                        try:
                            self.db_manager.update_session_game_time(session.id, result["new_time"])
                            session.game_time = result["new_time"]
                        except Exception as _e:
                            logger.error(f"Failed to update game time: {_e}")
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}")
                    tool_results.append({"tool_name": tool_name, "arguments": call.arguments, "error": str(e)})
                    
                    # Add error to tool calls panel
                    self.view.add_tool_result(str(e), is_error=True)

        # After executing tools, refresh memory inspector if a memory tool was used
        memory_tool_used = any(
            call.name in ["memory.upsert", "memory.update", "memory.delete", "memory.query"]
            for call in (plan.tool_calls or [])
        )
        
        if memory_tool_used and hasattr(self.view, 'memory_inspector'):
            # Schedule refresh on main thread
            self.view.after(100, self.view.memory_inspector.refresh_memories)

        # 2.5) Consistency audit (quick pass)
        try:
            audit_messages = self._get_truncated_history()
            audit_prompt = "You are a consistency auditor. In <=3 bullets, list contradictions between planned tool results and likely world state; else say OK. If patches are needed, propose minimal JSON patches."
            from app.io.schemas import AuditResult
            audit_dict = self.llm_connector.get_structured_response(
                system_prompt=audit_prompt,
                chat_history=audit_messages + [Message(role="system", content=str(tool_results))],
                output_schema=AuditResult
            )
            audit = AuditResult.model_validate(audit_dict)
            if not audit.ok:
                for patch in audit.proposed_patches or []:
                    args = {"entity_type": patch.entity_type, "key": patch.key, "patch": [op.model_dump() for op in patch.ops]}
                    _ = self.tool_registry.execute_tool("state.apply_patch", args, context={"session_id": session.id, "db_manager": self.db_manager})
                for mem in audit.memory_updates or []:
                    args = {"kind": mem.kind, "content": mem.content, "priority": mem.priority, "tags": mem.tags}
                    _ = self.tool_registry.execute_tool("memory.upsert", args, context={"session_id": session.id, "db_manager": self.db_manager, "vector_store": self.vector_store})
        except Exception as e:
            logger.debug(f"Audit skipped: {e}")

        # 3) Narrative + proposals
        try:
            chat_history = self._get_truncated_history()

            tool_results_str = str(tool_results)
            base_narrative_template = NARRATIVE_TEMPLATE.format(
                identity=chat_history[0].content,
                planner_thought=plan.thought,
                tool_results=tool_results_str
            )
            system_prompt_narrative = self._assemble_context(base_narrative_template, session)
            
            narrative_dict = self.llm_connector.get_structured_response(
                system_prompt=system_prompt_narrative,
                chat_history=chat_history,
                output_schema=NarrativeStep
            )
            narrative = NarrativeStep.model_validate(narrative_dict)
        except Exception as e:
            logger.error(f"Error during narrative generation: {e}", exc_info=True)
            self.view.add_message_bubble("system", f"Error during narrative: {e}")
            return

        self.view.add_message_bubble("assistant", narrative.narrative)
        self.session.add_message("assistant", narrative.narrative)

        # Store turn metadata
        if session.id:
            try:
                round_number = len(self.session.get_history()) // 2
                
                # Store in SQL database
                self.db_manager.create_turn_metadata(
                    session_id=session.id,
                    prompt_id=session.prompt_id,
                    round_number=round_number,
                    summary=narrative.turn_summary,
                    tags=narrative.turn_tags,
                    importance=narrative.turn_importance
                )
                
                # Store in vector database for semantic search
                self.vector_store.add_turn(
                    session_id=session.id,
                    prompt_id=session.prompt_id,  # 🆕 Pass prompt_id
                    round_number=round_number,
                    summary=narrative.turn_summary,
                    tags=narrative.turn_tags,
                    importance=narrative.turn_importance
                )
                
                logger.debug(f"Stored metadata for turn {round_number}")
                
                # 🆕 Check if we should create a rolling summary
                if round_number % 50 == 0:
                    self._create_rolling_summary(session)
                    
                    # Show memory stats before/after
                    stats_before = self.db_manager.get_memory_statistics(session.id)
                    self._optimize_procedural_memory(session)
                    stats_after = self.db_manager.get_memory_statistics(session.id)
                    
                    logger.info(f"Memory count: {stats_before['total']} → {stats_after['total']}")
            
            except Exception as e:
                logger.error(f"Error storing turn metadata: {e}", exc_info=True)

        # 4) Apply patches and memories
        if narrative.proposed_patches:
            for patch in narrative.proposed_patches:
                try:
                    args = {"entity_type": patch.entity_type, "key": patch.key, "patch": [op.model_dump() for op in patch.ops]}
                    result = self.tool_registry.execute_tool("state.apply_patch", args)
                    if self.tool_event_callback:
                        self.tool_event_callback(f"state.apply_patch ✓ -> {result}")
                except Exception as e:
                    logger.error(f"Patch error: {e}")

        if narrative.memory_intents:
            for mem in narrative.memory_intents:
                try:
                    args: Dict[str, Any] = {"kind": mem.kind, "content": mem.content}
                    if mem.priority is not None:
                        args["priority"] = int(mem.priority)  # Ensure it's an int
                    if mem.tags is not None:
                        args["tags"] = list(mem.tags)  # Ensure it's a list of strings
                    else:
                        args["tags"] = [] # Default to empty list if None
                    
                    context = {
                        "session_id": session.id,
                        "db_manager": self.db_manager,
                        "vector_store": self.vector_store,
                    }
                    
                    result = self.tool_registry.execute_tool("memory.upsert", args, context=context)
                    if self.tool_event_callback:
                        self.tool_event_callback(f"memory.upsert ✓ -> {result}")
                except Exception as e:
                    logger.error(f"Memory error: {e}")

        # 5) Generate action choices
        try:
            choice_template = CHOICE_GENERATION_TEMPLATE.format(
                narrative=narrative.narrative
            )
            system_prompt_choices = self._assemble_context(choice_template, session)
            
            chat_history = self._get_truncated_history()
            choices_dict = self.llm_connector.get_structured_response(
                system_prompt=system_prompt_choices,
                chat_history=chat_history,
                output_schema=ActionChoices
            )
            action_choices = ActionChoices.model_validate(choices_dict)
            
            # Display the choices in the UI
            self.view.display_action_choices(action_choices.choices)
        except Exception as e:
            logger.error(f"Error generating action choices: {e}", exc_info=True)

        # Persist session
        self.update_game(session)

    def run(self):
        self.view.mainloop()

    def new_session(self, system_prompt: str):
        self.session = Session("default_session", system_prompt=system_prompt)

    def save_game(self, name: str, prompt_id: int):
        if not self.session:
            return
        session_data = self.session.to_json()
        self.db_manager.save_session(name, session_data, prompt_id)

    def load_game(self, session_id: int):
        game_session = self.db_manager.load_session(session_id)
        if game_session:
            self.session = Session.from_json(game_session.session_data)

    def update_game(self, session: GameSession):
        if not self.session:
            return
        session.session_data = self.session.to_json()
        self.db_manager.update_session(session)


    def _format_turn_metadata_for_context(self, turns: List[Dict[str, Any]]) -> str:
        """Format turn metadata for inclusion in the system prompt."""
        if not turns:
            return ""
        
        lines = ["# RELEVANT PAST EVENTS #"]
        
        for turn in turns:
            importance_stars = "★" * turn["importance"]
            tags_str = f" [{', '.join(turn['tags'])}]" if turn['tags'] else ""
            
            lines.append(
                f"Turn {turn['round_number']} ({importance_stars}){tags_str}\n"
                f"   {turn['summary']}"
            )
        
        lines.append("")  # Empty line after
        return "\n".join(lines)

    def _create_rolling_summary(self, session: GameSession):
        """
        Every 50 rounds, create a chapter summary from metadata.
        """
        if not self.session: # Add this check
            logger.warning("No active session for rolling summary.")
            return
        if not session.id:
            return
        
        # Calculate the current round number
        current_round: int = len(self.session.get_history()) // 2
        
        # Only create summary at 50, 100, 150, etc.
        if current_round % 50 != 0:
            return
        
        chapter_num = current_round // 50
        start_round = (chapter_num - 1) * 50 + 1
        end_round = current_round
        
        logger.info(f"Creating rolling summary for rounds {start_round}-{end_round}")
        
        # Get all metadata from this chapter
        chapter_metadata = self.db_manager.get_turn_metadata_range(
            session.id, start_round, end_round
        )
        
        if not chapter_metadata:
            logger.warning("No metadata found for rolling summary")
            return
        
        # Format metadata for the prompt
        metadata_text = "\n".join([
            f"Turn {m['round_number']} (Importance: {m['importance']}): {m['summary']}"
            for m in chapter_metadata
        ])
        
        # Create summary prompt
        summary_prompt = f"""You are summarizing a chapter of an ongoing RPG story.

        Rounds {start_round}-{end_round} Summaries:
        {metadata_text}

        Create a cohesive narrative summary (2-3 paragraphs) that captures:
        - Major plot developments and story progression
        - Key character moments and decisions
        - Important discoveries, battles, or revelations
        - How the situation has changed from start to end

        Focus on the most important events (importance 4-5) but weave in context from other turns.
        Write in past tense, third person, as a story recap.
        """
        
        try:
            # Generate summary (streaming to get plain text)
            summary_parts = []
            for chunk in self.llm_connector.get_streaming_response(
                system_prompt="You are a narrative summarizer for an RPG game.",
                chat_history=[Message(role="user", content=summary_prompt)]
            ):
                summary_parts.append(chunk)
            
            summary = "".join(summary_parts).strip()
            
            # Store as high-priority episodic memory
            self.db_manager.create_memory(
                session_id=session.id,
                kind="episodic",
                content=f"[Chapter {chapter_num} Summary - Rounds {start_round}-{end_round}]\n\n{summary}",
                priority=5,
                tags=[f"chapter_{chapter_num}", "summary", "chapter_summary"]
            )
            
            logger.info(f"Created chapter {chapter_num} summary")
            
            # Optionally show in UI
            if self.tool_event_callback:
                self.tool_event_callback(f"📖 Chapter {chapter_num} summary created")
        
        except Exception as e:
            logger.error(f"Error creating rolling summary: {e}", exc_info=True)

    def _optimize_procedural_memory(self, session: GameSession):
        """
        Clean up low-value memories to prevent database bloat.
        Called every 50 rounds along with rolling summaries.
        
        Strategy:
        - Keep all high-priority memories (4-5)
        - Keep recently accessed memories (last 20 rounds)
        - Delete old, low-priority, rarely-accessed memories
        - Keep at least 50 memories (safety buffer)
        """
        if not session.id:
            return
        
        try:
            all_memories = self.db_manager.get_memories_by_session(session.id)
            
            # Need at least some memories to optimize
            if len(all_memories) < 100:
                logger.debug(f"Only {len(all_memories)} memories, skipping optimization")
                return
            
            candidates_for_deletion = []
            
            for mem in all_memories:
                # Always keep high-priority memories
                if mem.priority >= 4:
                    continue
                
                # Always keep recently accessed
                if mem.access_count > 0 and mem.last_accessed:
                    try:
                        from datetime import datetime, timedelta
                        last_access = datetime.fromisoformat(mem.last_accessed)
                        if datetime.now() - last_access < timedelta(hours=1):
                            continue
                    except (ValueError, AttributeError):
                        pass
                
                # Calculate a "staleness" score
                age_rounds = 999  # Default for old memories
                try:
                    from datetime import datetime
                    created = datetime.fromisoformat(mem.created_at)
                    age_days = (datetime.now() - created).days
                    age_rounds = age_days * 10  # Rough estimate
                except (ValueError, AttributeError):
                    pass
                
                # Delete if:
                # - Low priority (1-2)
                # - Never or rarely accessed (< 3 times)
                # - Created more than 10 rounds ago
                if (mem.priority <= 2 and 
                    mem.access_count < 3 and 
                    age_rounds > 10):
                    candidates_for_deletion.append(mem)
            
            # Safety: never delete more than 30% of memories at once
            max_deletions = len(all_memories) // 3
            to_delete = candidates_for_deletion[:max_deletions]
            
            # Safety: keep at least 50 memories
            if len(all_memories) - len(to_delete) < 50:
                keep_count = len(all_memories) - 50
                to_delete = to_delete[:max(0, keep_count)]
            
            if not to_delete:
                logger.debug("No memories need optimization")
                return
            
            # Delete the memories
            deleted_count = 0
            for mem in to_delete:
                try:
                    self.db_manager.delete_memory(mem.id)
                    
                    # Also remove from vector store
                    if self.vector_store:
                        try:
                            self.vector_store.delete_memory(session.id, mem.id)
                        except Exception:
                            pass
                    
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete memory {mem.id}: {e}")
            
            logger.info(f"Memory optimization: deleted {deleted_count} low-value memories (kept {len(all_memories) - deleted_count})")
            
            # Optionally notify user
            if self.tool_event_callback:
                self.tool_event_callback(f"🧹 Optimized {deleted_count} old memories")
        
        except Exception as e:
            logger.error(f"Error optimizing procedural memory: {e}", exc_info=True)
