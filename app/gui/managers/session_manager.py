"""
Manages game session CRUD operations and UI.
"""

import logging
from datetime import datetime
from typing import Callable, Optional

import customtkinter as ctk

from app.gui.styles import get_button_style
from app.gui.utils.ui_helpers import get_mode_display
from app.models.game_session import GameSession
from app.models.prompt import Prompt
from app.setup.scaffolding import inject_setup_scaffolding
from app.setup.schemas import CharacterExtraction, WorldExtraction
from app.setup.setup_manifest import SetupManifest
from app.tools.builtin._state_storage import get_entity, set_entity

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages game session operations and selection.
    """

    def __init__(
        self,
        orchestrator,
        db_manager,
        session_scrollable_frame: ctk.CTkScrollableFrame,
        session_name_label: ctk.CTkLabel,
        game_time_label: ctk.CTkLabel,
        game_mode_label: ctk.CTkLabel,
        send_button: ctk.CTkButton,
        session_collapsible,
        bubble_manager,
        authors_note_textbox: ctk.CTkTextbox,
        on_session_loaded_callback: Optional[Callable] = None,
    ):
        """
        Initializes the SessionManager.

        Args:
            orchestrator: The main orchestrator instance.
            db_manager: The database manager instance.
            session_name_label: Label to display the current session name.
            session_scrollable_frame: Frame to hold session buttons.
            game_time_label: Label to display the current game time.
            game_mode_label: Label to display the current game mode.
            send_button: Send button to enable/disable
            session_collapsible: Collapsible frame container
            authors_note_textbox: Author's Notes textbox
            bubble_manager: The ChatBubbleManager instance.
            on_session_loaded_callback: Optional callback to run after session loads
        """
        self.orchestrator = orchestrator
        self.db_manager = db_manager
        self.session_scrollable_frame = session_scrollable_frame
        self.session_name_label = session_name_label
        self.game_time_label = game_time_label
        self.game_mode_label = game_mode_label
        self.send_button = send_button
        self.session_collapsible = session_collapsible
        self.bubble_manager = bubble_manager
        self.authors_note_textbox = authors_note_textbox
        self._selected_session: Optional[GameSession] = None
        self.on_session_loaded_callback = on_session_loaded_callback

    @property
    def selected_session(self) -> Optional[GameSession]:
        """
        Get the currently selected session.
        """
        return self._selected_session

    def new_game(self, selected_prompt: Prompt):
        """
        Create a new game session with initial GM message and scaffolding.
        """
        if not selected_prompt:
            return

        # Launch the Setup Wizard instead of creating immediately
        from app.gui.panels.setup_wizard import SetupWizard

        # We pass 'self' so the wizard can call create_session_from_wizard upon completion
        wizard = SetupWizard(
            self.orchestrator.view,
            self.db_manager,
            self.orchestrator,
            selected_prompt,
            session_manager=self,
        )
        self.orchestrator.view.wait_window(wizard)

    def create_session_from_wizard(
        self,
        prompt: Prompt,
        char_data: CharacterExtraction,
        world_data: WorldExtraction,
        opening_crawl: str,
    ):
        """
        Finalize setup: Create DB rows, inject extracted data, and start gameplay.
        Called by SetupWizard.
        """
        # 1. Create Basic Session
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        session_name = f"{timestamp}_{prompt.name}"

        self.orchestrator.new_session(prompt.content, prompt.template_manifest)

        # 2. Inject Opening Crawl as first message
        self.orchestrator.session.add_message("assistant", opening_crawl)

        # 3. Persist Session to get ID
        self.orchestrator.save_game(session_name, prompt.id)
        session_id = self.orchestrator.session.id

        # 4. Inject Scaffolding (Ruleset, Template, Default Player)
        inject_setup_scaffolding(session_id, prompt.template_manifest, self.db_manager)

        # 5. Apply Extracted Character Data
        self._apply_character_extraction(session_id, char_data)

        # 6. Apply Extracted World Data
        self._apply_world_extraction(session_id, world_data)

        # 7. Set Game Mode to GAMEPLAY
        session = self.db_manager.sessions.get_by_id(session_id)
        session.game_mode = "GAMEPLAY"
        self.db_manager.sessions.update(session)

        # 8. Reload and Refresh UI
        self.refresh_session_list(prompt.id)
        self.on_session_select(
            session, self.bubble_manager, self.orchestrator.view.inspector_manager.views
        )
        logger.info(f"Session '{session_name}' created via Wizard.")

    def _apply_character_extraction(
        self, session_id: int, char_data: CharacterExtraction
    ):
        """Updates the scaffolded player entity with extracted details."""
        player = get_entity(session_id, self.db_manager, "character", "player")
        if not player:
            return

        # Update Bio
        player["name"] = char_data.name
        player["description"] = char_data.visual_description
        # Note: We could store 'bio' in a memory or a notes field on the char

        # Update Stats (Best Effort Mapping)
        # We assume 'suggested_stats' keys might match Ability names
        if "abilities" in player:
            for stat_name, val in char_data.suggested_stats.items():
                # Try exact match
                if stat_name in player["abilities"]:
                    player["abilities"][stat_name] = val
                else:
                    # Try case-insensitive match
                    for key in player["abilities"].keys():
                        if key.lower() == stat_name.lower():
                            player["abilities"][key] = val
                            break

        # Update Inventory (Simple string list to Item objects)
        # We find the first slot that looks like "Inventory"
        target_slot = None
        if "slots" in player and player["slots"]:
            keys = list(player["slots"].keys())

            # 1. Priority search for keywords
            for k in keys:
                k_lower = k.lower()
                if (
                    "inventory" in k_lower
                    or "gear" in k_lower
                    or "backpack" in k_lower
                    or "cargo" in k_lower
                ):
                    target_slot = k
                    break

            # 2. Fallback: Just use the first available slot (e.g. "Loadout")
            if not target_slot and keys:
                target_slot = keys[0]

        # 3. Final Fallback if slots dict is empty
        if not target_slot:
            target_slot = "Inventory"

            # Create item objects
            items = []
            for item_str in char_data.inventory:
                items.append(
                    {
                        "name": item_str,
                        "quantity": 1,
                        "description": "Starting equipment",
                    }
                )
            player["slots"][target_slot] = items

        set_entity(session_id, self.db_manager, "character", "player", player)

        # Spawn Companions (Pets, Familiars)
        # They spawn at the player's location (which isn't set yet, but will be in next step)
        # We'll handle location linkage in _apply_world_extraction or just let them float until scene update
        for npc in char_data.companions:
            # Use a distinct key
            key = f"companion_{npc.name_display.lower().replace(' ', '_')}"
            self._create_npc_entity(session_id, key, npc, disposition="friendly")

    def _apply_world_extraction(self, session_id: int, world_data: WorldExtraction):
        """Creates location, lore, and NPCs."""

        # 0. NEW: Update Session Manifest with Extracted Tone/Genre
        # This persists the "Vibe" for future AI turns.
        manifest_mgr = SetupManifest(self.db_manager)
        manifest_mgr.update_manifest(
            session_id, {"genre": world_data.genre, "tone": world_data.tone}
        )

        # 1. Create Location
        loc = world_data.starting_location
        loc_data = {
            "name": loc.name_display,
            "description_visual": loc.description_visual,
            "description_sensory": loc.description_sensory,
            "type": loc.type,
            "connections": {},
        }
        set_entity(session_id, self.db_manager, "location", loc.key, loc_data)

        # 2. Update Scene
        scene = get_entity(session_id, self.db_manager, "scene", "active_scene")
        if scene:
            scene["location_key"] = loc.key
            set_entity(session_id, self.db_manager, "scene", "active_scene", scene)

        # 2. Create Lore Memories
        for mem in world_data.lore:
            created_mem = self.db_manager.memories.create(
                session_id, mem.kind, mem.content, mem.priority, mem.tags
            )
            # FIX: Push to Vector Store
            if self.orchestrator.vector_store:
                try:
                    self.orchestrator.vector_store.upsert_memory(
                        session_id,
                        created_mem.id,
                        created_mem.content,
                        created_mem.kind,
                        created_mem.tags_list(),
                        created_mem.priority,
                    )
                except Exception as e:
                    logger.error(f"Failed to embed initial lore: {e}")

        # Collect member IDs for the scene
        scene_members = ["character:player"]

        # 4. Spawn World NPCs
        for npc in world_data.initial_npcs:
            key = f"npc_{npc.name_display.lower().replace(' ', '_')}"
            npc.location_key = loc.key
            self._create_npc_entity(
                session_id, key, npc, disposition=npc.initial_disposition
            )
            scene_members.append(f"character:{key}")

        # 5. Ensure Companions...
        all_chars = self.db_manager.game_state.get_all_entities_by_type(
            session_id, "character"
        )
        for key, data in all_chars.items():
            if key.startswith("companion_"):
                data["location_key"] = loc.key
                set_entity(session_id, self.db_manager, "character", key, data)
                scene_members.append(f"character:{key}")

        # 6. Initialize Active Scene
        scene_data = {
            "location_key": loc.key,
            "members": scene_members,
            "state_tags": ["exploration"],
        }
        set_entity(session_id, self.db_manager, "scene", "active_scene", scene_data)
        # Cleanup temp storage
        if hasattr(self, "_pending_scene_members"):
            del self._pending_scene_members

    def _create_npc_entity(self, session_id, key, npc_model, disposition="neutral"):
        """Helper to create raw NPC entity from extraction model."""
        npc_data = {
            "name": npc_model.name_display,
            "description": npc_model.visual_description,
            "disposition": disposition,
            "location_key": npc_model.location_key,  # Might be None initially
            "template_id": None,  # Could try to link to a 'Monster' template if available
            "abilities": {},  # Raw stats would need inference, leaving empty implies 'Commoner'
            "vitals": {"HP": {"current": 10, "max": 10}},
            "inventory": [],
            "conditions": [],
        }
        set_entity(session_id, self.db_manager, "character", key, npc_data)

        # FIX: Create NPC Profile (Brain)
        # Map extraction data to profile
        profile_data = {
            "personality_traits": [],  # Could extract this if we added it to extraction schema
            "motivations": ["Exist in the world"],
            "directive": "Patrol area" if disposition == "hostile" else "Wander",
            "knowledge_tags": ["world_gen"],
            "relationships": {},
            "last_updated_time": "Day 1, Dawn",
        }
        set_entity(session_id, self.db_manager, "npc_profile", key, profile_data)

    def load_game(self, session_id: int, bubble_manager):
        """
        Load a saved game session.

        Args:
            session_id: ID of the session to load
            bubble_manager: ChatBubbleManager instance for displaying history
        """
        # Load session via orchestrator
        self.orchestrator.load_game(session_id)

        # Clear existing chat
        bubble_manager.clear_history()

        # Replay history
        history = self.orchestrator.session.get_history()
        for message in history:
            if message.role == "user":
                bubble_manager.add_message("user", message.content)
            elif message.role == "assistant":
                bubble_manager.add_message("assistant", message.content)
            elif message.role == "system":
                bubble_manager.add_message("system", message.content)

    def on_session_select(self, session: GameSession, bubble_manager, inspectors: dict):
        """
        Handle session selection.

        Args:
            session: Selected session
            bubble_manager: ChatBubbleManager instance
            inspectors: Dictionary of inspector instances
        """
        self._selected_session = session
        self.load_game(session.id, bubble_manager)
        self.send_button.configure(state="normal")

        # Update header with session info
        self.session_name_label.configure(text=session.name)
        self.game_time_label.configure(text=f"{session.game_time}")

        # Update game mode indicator
        mode_text, mode_color = get_mode_display(session.game_mode)
        self.game_mode_label.configure(text=mode_text, text_color=mode_color)

        # Load context (Author's Note)
        self.load_context(self.authors_note_textbox)

        # Update memory inspector if available
        if "memory" in inspectors and inspectors["memory"]:
            inspectors["memory"].set_session(session.id)
            inspectors["memory"].refresh_memories()
        
        # Update map inspector if available
        if "map" in inspectors and inspectors["map"]:
            inspectors["map"].set_session(session.id)

        # Refresh all inspectors
        for inspector_name in ["character", "inventory", "quest", "map"]:
            if inspector_name in inspectors and inspectors[inspector_name]:
                inspectors[inspector_name].refresh()

        # Update button styles
        button_styles = get_button_style()
        selected_style = get_button_style("selected")

        for row_frame in self.session_scrollable_frame.winfo_children():
            # Ensure the child is a frame and has children before proceeding
            if isinstance(row_frame, ctk.CTkFrame) and row_frame.winfo_children():
                # The load button is the first child of the row_frame
                load_button = row_frame.winfo_children()[0]
                if isinstance(load_button, ctk.CTkButton):
                    if load_button.cget("text") == session.name:
                        load_button.configure(fg_color=selected_style["fg_color"])
                    else:
                        load_button.configure(fg_color=button_styles["fg_color"])

        # Collapse the session panel
        if self.session_collapsible and not self.session_collapsible.is_collapsed:
            self.session_collapsible.toggle()

        # Notify MainView that session was loaded
        if self.on_session_loaded_callback:
            self.on_session_loaded_callback()

    def refresh_session_list(self, prompt_id: int | None = None):
        """
        Refresh the session list UI.

        Args:
            prompt_id: Filter sessions by prompt ID (optional)
        """
        # Clear existing widgets
        for widget in self.session_scrollable_frame.winfo_children():
            widget.destroy()

        if prompt_id:
            # Get sessions for this prompt
            sessions = self.db_manager.sessions.get_by_prompt(prompt_id)

            # Create a frame with load/delete buttons for each session
            for session in sessions:
                row_frame = ctk.CTkFrame(
                    self.session_scrollable_frame, fg_color="transparent"
                )
                row_frame.pack(fill="x", pady=2, padx=5)

                load_btn = ctk.CTkButton(
                    row_frame,
                    text=session.name,
                    command=lambda s=session: self._on_button_click(s),
                )
                load_btn.pack(side="left", expand=True, fill="x")

                delete_btn = ctk.CTkButton(
                    row_frame,
                    text="🗑️",
                    command=lambda s=session: self.delete_session(s),
                    width=40,
                    fg_color="darkred",
                    hover_color="red",
                )
                delete_btn.pack(side="left", padx=(5, 0))

    def delete_session(self, session_to_delete: GameSession):
        """Delete a session after confirmation."""
        dialog = ctk.CTkInputDialog(
            text=f"This is irreversible.\nType DELETE to remove '{session_to_delete.name}':",
            title="Confirm Deletion",
        )
        result = dialog.get_input()

        if result == "DELETE":
            prompt_id = session_to_delete.prompt_id
            is_current_session = (
                self._selected_session
                and self._selected_session.id == session_to_delete.id
            )

            self.db_manager.sessions.delete(session_to_delete.id)
            # FIX: Ensure vector store data is also deleted
            if self.orchestrator.vector_store:
                self.orchestrator.vector_store.delete_session_data(session_to_delete.id)

            if is_current_session:
                self._clear_active_session_view()

            self.refresh_session_list(prompt_id)
            self.bubble_manager.add_message(
                "system", f"Deleted session '{session_to_delete.name}'"
            )

    def load_context(self, authors_note_textbox: ctk.CTkTextbox):
        """
        Load author's note for the current session.
        """
        import logging

        logger = logging.getLogger(__name__)

        if not self._selected_session:
            logger.debug("No session selected, skipping load_context")
            return

        # Load context from database
        context = self.db_manager.sessions.get_context(self._selected_session.id)

        if context:
            # Populate author's note textbox
            authors_note = context.get("authors_note", "")
            authors_note_textbox.delete("1.0", "end")
            authors_note_textbox.insert("1.0", authors_note)

            logger.debug(
                f"Loaded author's note ({len(authors_note)} chars) for session {self._selected_session.id}"
            )
        else:
            logger.warning(f"No context found for session {self._selected_session.id}")
            authors_note_textbox.delete("1.0", "end")

    def save_context(self, bubble_manager):
        """
        Save the author's note.

        MIGRATION NOTES:
        - Removed memory field (deprecated)
        """
        import logging

        logger = logging.getLogger(__name__)

        if not self._selected_session:
            logger.warning("No session selected, cannot save context")
            bubble_manager.add_message("system", "Please load a game session first")
            return

        try:
            # Get content from textbox
            authors_note = self.authors_note_textbox.get("1.0", "end-1c")

            logger.debug(
                f"Saving author's note for session {self._selected_session.id}"
            )
            logger.debug(f"   Author's Note length: {len(authors_note)} chars")

            # Save to database (memory field = empty string)
            self.db_manager.sessions.update_context(
                self._selected_session.id,
                "",  # memory field always empty now
                authors_note,
            )

            # Updates the in-memory session object
            self._selected_session.authors_note = authors_note

            logger.info(
                f"Context saved successfully for session {self._selected_session.id}"
            )

            # Show confirmation
            bubble_manager.add_message("system", "Author's Note saved")
        except Exception as e:
            logger.error(f"Error saving context: {e}", exc_info=True)
            bubble_manager.add_message("system", f"Error saving: {e}")

    def _clear_active_session_view(self):
        """Resets the UI to a neutral state when a session is deleted or unloaded."""
        self.bubble_manager.clear_history()
        self._selected_session = None
        self.orchestrator.session = None
        self.session_name_label.configure(text="No session loaded")
        self.game_time_label.configure(text="...")
        self.game_mode_label.configure(text="")
        self.send_button.configure(state="disabled")
        self.authors_note_textbox.delete("1.0", "end")

    def _on_button_click(self, session: GameSession):
        """
        Internal handler for session button clicks.
        """
        logger.warning("Session button clicked but dependencies not wired yet")
