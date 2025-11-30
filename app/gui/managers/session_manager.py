import json
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
from app.models.session import Session
from app.tools.builtin.location_create import handler as location_create_handler

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
        return self._selected_session

    def new_game(self, selected_prompt: Prompt):
        if not selected_prompt:
            return
        from app.gui.panels.setup_wizard import SetupWizard

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
        opening_crawl: str | None,
        generate_crawl: bool = True,
    ):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        session_name = f"{timestamp}_{prompt.name}"

        self.orchestrator.new_session(prompt.content, prompt.template_manifest)

        if generate_crawl and opening_crawl:
            self.orchestrator.session.add_message("assistant", opening_crawl)
        else:
            self.orchestrator.session.add_message(
                "system",
                f"Session initialized at {world_data.starting_location.name_display}. Waiting for player input.",
            )

        self.orchestrator.save_game(session_name, prompt.id)
        session_id = self.orchestrator.session.id

        # Inject scaffolding (Rules + Template)
        inject_setup_scaffolding(session_id, prompt.template_manifest, self.db_manager)

        # Apply Extraction Data
        self._apply_character_extraction(session_id, char_data)
        self._apply_world_extraction(session_id, world_data)

        # Finalize Session State
        session = self.db_manager.sessions.get_by_id(session_id)
        session.game_mode = "GAMEPLAY"

        setup_data = (
            json.loads(session.setup_phase_data) if session.setup_phase_data else {}
        )
        setup_data["initial_state"] = {
            "character_data": char_data.model_dump(),
            "world_data": world_data.model_dump(),
            "opening_crawl": opening_crawl,
        }
        session.setup_phase_data = json.dumps(setup_data)

        self.db_manager.sessions.update(session)

        self.refresh_session_list(prompt.id)

        # Refresh UI
        inspectors = {}
        if hasattr(self.orchestrator, "view") and hasattr(
            self.orchestrator.view, "inspector_manager"
        ):
            inspectors = self.orchestrator.view.inspector_manager.views

        self.on_session_select(session, self.bubble_manager, inspectors)
        logger.info(f"Session '{session_name}' created via Wizard.")

    def _apply_character_extraction(
        self, session_id: int, char_data: CharacterExtraction
    ):
        player = get_entity(session_id, self.db_manager, "character", "player")
        if not player:
            return

        player["name"] = char_data.name
        player["description"] = char_data.visual_description

        # Map Suggested Stats to Fundamentals/Gauges
        funds = player.setdefault("fundamentals", {})
        gauges = player.setdefault("gauges", {})

        for stat_name, val in char_data.suggested_stats.items():
            # Try exact match in Fundamentals
            if stat_name in funds:
                funds[stat_name] = val
                continue

            # Try exact match in Gauges (Set Current)
            if stat_name in gauges:
                gauges[stat_name]["current"] = val
                continue

            # Fuzzy match (Case-insensitive)
            found = False
            for k in funds.keys():
                if k.lower() == stat_name.lower():
                    funds[k] = val
                    found = True
                    break
            if found:
                continue

            for k in gauges.keys():
                if k.lower() == stat_name.lower():
                    gauges[k]["current"] = val
                    break

        # Map Inventory
        cols = player.setdefault("collections", {})
        target_col = "inventory"
        if "inventory" not in cols:
            if cols:
                target_col = next(iter(cols))
            else:
                cols["inventory"] = []

        target_list = cols.setdefault(target_col, [])
        for item_str in char_data.inventory:
            target_list.append({"name": item_str, "qty": 1})

        player["scene_state"] = {"zone_id": None, "is_hidden": False}
        set_entity(session_id, self.db_manager, "character", "player", player)

        # Spawn Companions
        for npc in char_data.companions:
            key = f"companion_{npc.name_display.lower().replace(' ', '_')}"
            self._create_npc_entity(session_id, key, npc, disposition="friendly")

    def _apply_world_extraction(self, session_id: int, world_data: WorldExtraction):
        SetupManifest(self.db_manager).update_manifest(
            session_id, {"genre": world_data.genre, "tone": world_data.tone}
        )

        loc = world_data.starting_location
        loc_data = {
            "name": loc.name_display,
            "description_visual": loc.description_visual,
            "description_sensory": loc.description_sensory,
            "type": loc.type,
            "connections": {},
        }
        set_entity(session_id, self.db_manager, "location", loc.key, loc_data)

        context = {"session_id": session_id, "db_manager": self.db_manager}
        for neighbor in world_data.adjacent_locations:
            args = neighbor.model_dump(exclude={"name"})
            try:
                location_create_handler(**args, **context)
            except Exception as e:
                logger.error(f"Failed to create adjacent location {neighbor.key}: {e}")

        scene = get_entity(session_id, self.db_manager, "scene", "active_scene")
        if scene:
            scene["location_key"] = loc.key
            set_entity(session_id, self.db_manager, "scene", "active_scene", scene)

        for mem in world_data.lore:
            created_mem = self.db_manager.memories.create(
                session_id, mem.kind, mem.content, mem.priority, mem.tags
            )
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
                except Exception:
                    pass

        scene_members = ["character:player"]

        for npc in world_data.initial_npcs:
            key = f"npc_{npc.name_display.lower().replace(' ', '_')}"
            npc.location_key = loc.key
            self._create_npc_entity(
                session_id, key, npc, disposition=npc.initial_disposition
            )
            scene_members.append(f"character:{key}")

        all_chars = self.db_manager.game_state.get_all_entities_by_type(
            session_id, "character"
        )
        for key, data in all_chars.items():
            if key.startswith("companion_"):
                data["location_key"] = loc.key
                set_entity(session_id, self.db_manager, "character", key, data)
                scene_members.append(f"character:{key}")

        scene_data = {
            "location_key": loc.key,
            "members": scene_members,
            "state_tags": ["exploration"],
            "layout_type": "default",
            "zones": [],
        }
        set_entity(session_id, self.db_manager, "scene", "active_scene", scene_data)

    def _create_npc_entity(self, session_id, key, npc_model, disposition="neutral"):
        npc_data = {
            "name": npc_model.name_display,
            "description": npc_model.visual_description,
            "disposition": disposition,
            "location_key": npc_model.location_key,
            "template_id": None,
            "fundamentals": {},
            "derived": {},
            "gauges": {"hp": {"current": 10, "max": 10}},
            "collections": {"inventory": []},
            "scene_state": {"zone_id": None, "is_hidden": False},
        }
        set_entity(session_id, self.db_manager, "character", key, npc_data)

        profile_data = {
            "personality_traits": [],
            "motivations": ["Exist in the world"],
            "directive": "Patrol area" if disposition == "hostile" else "Wander",
            "knowledge_tags": ["world_gen"],
            "relationships": {},
            "last_updated_time": "Day 1, Dawn",
        }
        set_entity(session_id, self.db_manager, "npc_profile", key, profile_data)

    def load_game(self, session_id: int, bubble_manager):
        self.orchestrator.load_game(session_id)
        bubble_manager.clear_history()
        history = self.orchestrator.session.get_history()
        for message in history:
            if message.role == "user":
                bubble_manager.add_message("user", message.content)
            elif message.role == "assistant":
                bubble_manager.add_message("assistant", message.content)
            elif message.role == "system":
                bubble_manager.add_message("system", message.content)

    def on_session_select(self, session: GameSession, bubble_manager, inspectors: dict):
        self._selected_session = session
        self.load_game(session.id, bubble_manager)
        self.send_button.configure(state="normal")
        self.session_name_label.configure(text=session.name)
        self.game_time_label.configure(text=f"{session.game_time}")
        mode_text, mode_color = get_mode_display(session.game_mode)
        self.game_mode_label.configure(text=mode_text, text_color=mode_color)
        self.load_context(self.authors_note_textbox)

        if "memory" in inspectors and inspectors["memory"]:
            inspectors["memory"].set_session(session.id)
            inspectors["memory"].refresh_memories()

        if "map" in inspectors and inspectors["map"]:
            inspectors["map"].set_session(session.id)

        for inspector_name in ["character", "inventory", "quest", "map", "scene_map"]:
            if inspector_name in inspectors and inspectors[inspector_name]:
                try:
                    inspectors[inspector_name].refresh()
                except Exception as e:
                    logger.error(f"Error refreshing inspector {inspector_name}: {e}")

        # Update button styles
        button_styles = get_button_style()
        selected_style = get_button_style("selected")

        for row_frame in self.session_scrollable_frame.winfo_children():
            if isinstance(row_frame, ctk.CTkFrame) and row_frame.winfo_children():
                load_button = row_frame.winfo_children()[0]
                if isinstance(load_button, ctk.CTkButton):
                    if load_button.cget("text") == session.name:
                        load_button.configure(fg_color=selected_style["fg_color"])
                    else:
                        load_button.configure(fg_color=button_styles["fg_color"])

        if self.session_collapsible and not self.session_collapsible.is_collapsed:
            self.session_collapsible.toggle()

        if self.on_session_loaded_callback:
            self.on_session_loaded_callback()

    def refresh_session_list(self, prompt_id: int | None = None):
        """
        Refresh the session list UI.
        """
        # Clear existing widgets
        for widget in self.session_scrollable_frame.winfo_children():
            widget.destroy()

        if prompt_id:
            sessions = self.db_manager.sessions.get_by_prompt(prompt_id)

            for session in sessions:
                row_frame = ctk.CTkFrame(
                    self.session_scrollable_frame, fg_color="transparent"
                )
                row_frame.pack(fill="x", pady=2, padx=5)

                # Load Button
                load_btn = ctk.CTkButton(
                    row_frame,
                    text=session.name,
                    command=lambda s=session: self._on_button_click(s),
                )
                load_btn.pack(side="left", expand=True, fill="x")

                # Edit Button (Rename)
                edit_btn = ctk.CTkButton(
                    row_frame,
                    text="âœ ï¸ ",
                    width=30,
                    fg_color="gray",
                    command=lambda s=session: self.edit_session_name(s),
                )
                edit_btn.pack(side="left", padx=(5, 0))

                # Clone Button
                clone_btn = ctk.CTkButton(
                    row_frame,
                    text="ðŸ“‹",
                    width=30,
                    fg_color="gray",
                    command=lambda s=session: self.clone_session(s),
                )
                clone_btn.pack(side="left", padx=(5, 0))

                # Delete Button
                delete_btn = ctk.CTkButton(
                    row_frame,
                    text="ðŸ—‘ï¸ ",
                    command=lambda s=session: self.delete_session(s),
                    width=40,
                    fg_color="darkred",
                    hover_color="red",
                )
                delete_btn.pack(side="left", padx=(5, 0))

    def edit_session_name(self, session: GameSession):
        """Rename a session."""
        dialog = ctk.CTkInputDialog(
            text="Enter new session name:", title="Rename Session"
        )
        new_name = dialog.get_input()

        if new_name and len(new_name.strip()) > 0:
            session.name = new_name.strip()
            self.db_manager.sessions.update(session)

            if self._selected_session and self._selected_session.id == session.id:
                self.session_name_label.configure(text=session.name)

            self.refresh_session_list(session.prompt_id)

    def clone_session(self, source_session: GameSession):
        """Clone a session."""
        try:
            setup_data = (
                json.loads(source_session.setup_phase_data)
                if source_session.setup_phase_data
                else {}
            )
            initial_state = setup_data.get("initial_state")

            if not initial_state:
                logger.warning(
                    f"Cannot clone session {source_session.id}: No initial state."
                )
                self.bubble_manager.add_message(
                    "system", "âš ï¸  Cannot clone this session (Old format)."
                )
                return

            char_data = CharacterExtraction(**initial_state["character_data"])
            world_data = WorldExtraction(**initial_state["world_data"])
            opening_crawl = initial_state.get("opening_crawl")

            new_name = f"{source_session.name} - branch"

            new_session = self.db_manager.sessions.create(
                new_name,
                source_session.session_data,
                source_session.prompt_id,
                source_session.setup_phase_data,
            )

            clean_session = Session(f"session_{new_session.id}")
            if opening_crawl:
                clean_session.add_message("assistant", opening_crawl)
            else:
                clean_session.add_message("system", "Session cloned.")

            new_session.session_data = clean_session.to_json()
            new_session.game_mode = "GAMEPLAY"
            self.db_manager.sessions.update(new_session)

            self._apply_character_extraction(new_session.id, char_data)
            self._apply_world_extraction(new_session.id, world_data)

            self.refresh_session_list(source_session.prompt_id)
            self.bubble_manager.add_message(
                "system", f"âœ… Cloned '{source_session.name}' successfully."
            )

        except Exception as e:
            logger.error(f"Clone failed: {e}", exc_info=True)
            self.bubble_manager.add_message("system", f"â Œ Clone failed: {e}")

    def delete_session(self, session_to_delete: GameSession):
        """Delete a session."""
        dialog = ctk.CTkInputDialog(
            text=f"Type DELETE to remove '{session_to_delete.name}':",
            title="Confirm Deletion",
        )
        result = dialog.get_input()

        if result == "DELETE":
            prompt_id = session_to_delete.prompt_id
            is_current = (
                self._selected_session
                and self._selected_session.id == session_to_delete.id
            )

            self.db_manager.sessions.delete(session_to_delete.id)
            if self.orchestrator.vector_store:
                self.orchestrator.vector_store.delete_session_data(session_to_delete.id)

            if is_current:
                self._clear_active_session_view()

            self.refresh_session_list(prompt_id)
            self.bubble_manager.add_message(
                "system", f"Deleted session '{session_to_delete.name}'"
            )

    def load_context(self, authors_note_textbox: ctk.CTkTextbox):
        if not self._selected_session:
            return
        context = self.db_manager.sessions.get_context(self._selected_session.id)
        if context:
            authors_note_textbox.delete("1.0", "end")
            authors_note_textbox.insert("1.0", context.get("authors_note", ""))

    def save_context(self, bubble_manager):
        if not self._selected_session:
            return
        authors_note = self.authors_note_textbox.get("1.0", "end-1c")
        self.db_manager.sessions.update_context(
            self._selected_session.id, "", authors_note
        )
        self._selected_session.authors_note = authors_note
        bubble_manager.add_message("system", "Author's Note saved")

    def _clear_active_session_view(self):
        self.bubble_manager.clear_history()
        self._selected_session = None
        self.orchestrator.session = None
        self.session_name_label.configure(text="No session loaded")
        self.game_time_label.configure(text="...")
        self.game_mode_label.configure(text="")
        self.send_button.configure(state="disabled")
        self.authors_note_textbox.delete("1.0", "end")

    def _on_button_click(self, session: GameSession):
        # Delegate to on_session_select, but we need inspector refs.
        # This is usually handled by the lambda in refresh_session_list
        # This method is just a type-hinted stub for internals
        pass
