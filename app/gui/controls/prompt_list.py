from nicegui import ui
from app.gui.dialogs.setup_wizard import SetupWizard
from app.gui.dialogs.prompt_editor import PromptEditorDialog


class PromptListComponent:
    def __init__(self, db_manager, orchestrator, session_list_ref):
        self.db = db_manager
        self.orchestrator = orchestrator
        self.session_list = session_list_ref
        self.container = None

        # Reusable session delete dialog state
        self.delete_dialog = None
        self.delete_dialog_label = None
        self._session_to_delete = None

    def render(self):
        self.container = ui.column().classes("w-full gap-2")

        # Persistent delete-session dialog
        with ui.dialog() as self.delete_dialog, ui.card():
            self.delete_dialog_label = ui.label("Delete session?").classes("font-bold")
            with ui.row().classes("w-full justify-end mt-2"):
                ui.button("Cancel", on_click=self.delete_dialog.close).props("flat")
                ui.button("Delete", on_click=self._execute_delete_session).classes(
                    "bg-red-600"
                )

        self.refresh()

    def refresh(self):
        if not self.container:
            return

        self.container.clear()
        prompts = self.db.prompts.get_all()
        active_session = self.session_list.get_active_session()

        with self.container:
            # Header
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Game Systems").classes("text-sm font-bold text-gray-400")
                ui.button(icon="add", on_click=self.create_prompt).props(
                    "flat dense round"
                ).tooltip("Create New System")

            if not prompts:
                ui.label("No Systems Found").classes("text-gray-500 italic text-sm")
                return

            for prompt in prompts:
                sessions = self.db.sessions.get_by_prompt(prompt.id)

                with ui.expansion(prompt.name, icon="description").classes(
                    "w-full bg-slate-800 border border-slate-700 rounded"
                ):
                    # Prompt header row (actions)
                    with ui.row().classes("w-full items-center justify-between mb-1"):
                        ui.label(prompt.name).classes("font-bold text-gray-200")
                        with ui.row().classes("gap-1"):
                            ui.button(
                                icon="play_arrow",
                                on_click=lambda p=prompt: self.start_wizard(p),
                            ).props("flat dense round").classes(
                                "text-green-400"
                            ).tooltip("Start New Game")

                            ui.button(
                                icon="edit",
                                on_click=lambda p=prompt: self.edit_prompt(p),
                            ).props("flat dense round").classes(
                                "text-gray-500"
                            ).tooltip("Edit System")

                            ui.button(
                                icon="delete",
                                on_click=lambda p=prompt: self.delete_prompt(p),
                            ).props("flat dense round").classes("text-red-500").tooltip(
                                "Delete System"
                            )

                    ui.separator().classes("my-2 bg-slate-700/60")

                    ui.label("Saved Games").classes(
                        "text-xs font-bold text-gray-500 uppercase mb-1"
                    )

                    if not sessions:
                        ui.label("No saves for this system yet.").classes(
                            "text-xs text-gray-500 italic"
                        )
                    else:
                        for sess in sessions:
                            is_active = (
                                active_session is not None
                                and active_session.id == sess.id
                            )
                            bg = "bg-slate-700" if is_active else "bg-slate-900/60"

                            with ui.row().classes(
                                f"w-full p-2 rounded cursor-pointer {bg} "
                                "items-center justify-between group"
                            ):
                                # Clickable area to load session
                                with (
                                    ui.row()
                                    .classes("flex-grow items-center gap-2")
                                    .on(
                                        "click",
                                        lambda s=sess: self.session_list.load_session(
                                            s
                                        ),
                                    )
                                ):
                                    ui.icon("history").classes("text-gray-500")
                                    with ui.column().classes("gap-0"):
                                        ui.label(sess.name).classes("font-bold text-sm")
                                        ui.label(sess.game_time or "").classes(
                                            "text-xs text-gray-400"
                                        )

                                # Per-session actions menu
                                with (
                                    ui.button(icon="more_vert")
                                    .props("flat dense round size=sm")
                                    .classes(
                                        "text-gray-400 opacity-0 group-hover:opacity-100"
                                    )
                                ):
                                    with ui.menu():
                                        ui.menu_item(
                                            "Load",
                                            on_click=lambda s=sess: self.session_list.load_session(
                                                s
                                            ),
                                        )
                                        ui.menu_item(
                                            "Rename",
                                            on_click=lambda s=sess: self.rename_session(
                                                s
                                            ),
                                        )
                                        ui.menu_item(
                                            "Clone",
                                            on_click=lambda s=sess: self.clone_session(
                                                s
                                            ),
                                        )
                                        ui.separator()
                                        ui.menu_item(
                                            "Delete",
                                            on_click=lambda s=sess: self.confirm_delete(
                                                s
                                            ),
                                        ).classes("text-red-400")

    def create_prompt(self):
        dialog = PromptEditorDialog(self.db, self.orchestrator, on_save=self.refresh)
        dialog.open()

    def edit_prompt(self, prompt):
        # Fetch full prompt data (get_all is usually lightweight)
        full_prompt = self.db.prompts.get_by_id(prompt.id)
        dialog = PromptEditorDialog(
            self.db, self.orchestrator, prompt=full_prompt, on_save=self.refresh
        )
        dialog.open()

    def delete_prompt(self, prompt):
        # Confirm
        with ui.dialog() as dialog, ui.card():
            ui.label(f"Delete System '{prompt.name}'?")
            ui.label("This will NOT delete save files, but they may break.").classes(
                "text-xs text-red-400"
            )
            with ui.row().classes("justify-end"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button(
                    "Delete", on_click=lambda: self._do_delete(prompt, dialog)
                ).classes("bg-red-600")
        dialog.open()

    def _do_delete(self, prompt, dialog):
        self.db.prompts.delete(prompt.id)
        dialog.close()
        self.refresh()
        ui.notify(f"Deleted {prompt.name}")

    def start_wizard(self, prompt):
        # Load full prompt to get template manifest
        full_prompt = self.db.prompts.get_by_id(prompt.id)

        def _on_complete():
            # 1) Refresh the Systems & Saves list so the new session appears
            self.refresh()

            # 2) Auto-load the newly created session into the UI
            #    SetupWizard.finish() already called orchestrator.load_game(new_id),
            #    so orchestrator.session.id should be the new GameSession ID.
            sess_model = self.orchestrator.session
            if sess_model and sess_model.id:
                new_game_session = self.db.sessions.get_by_id(sess_model.id)
                if new_game_session:
                    self.session_list.load_session(new_game_session)

        wizard = SetupWizard(
            self.db,
            self.orchestrator,
            full_prompt,
            on_complete=_on_complete,
        )
        wizard.open()

    def rename_session(self, session):
        with ui.dialog() as dialog, ui.card():
            ui.label("Rename Session").classes("font-bold")
            name_input = ui.input(value=session.name).classes("w-full")

            def save():
                session.name = name_input.value
                self.db.sessions.update(session)
                self.refresh()
                dialog.close()

            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button("Save", on_click=save)
        dialog.open()

    def clone_session(self, session):
        import logging

        logger = logging.getLogger(__name__)

        try:
            new_name = f"{session.name} (Clone)"
            ui.notify("Cloning... please wait.")

            # 1. Duplicate Session Row
            new_sess = self.db.sessions.create(
                name=new_name,
                session_data=session.session_data,
                prompt_id=session.prompt_id,
                setup_phase_data=session.setup_phase_data,
            )

            # 2. Clone Game State
            state_data = self.db.game_state.get_all(session.id)
            for etype, items in state_data.items():
                for key, val in items.items():
                    self.db.game_state.set_entity(new_sess.id, etype, key, val["data"])

            # 3. Clone & Re-Index Memories
            mems = self.db.memories.get_by_session(session.id)
            vs = self.orchestrator.vector_store

            for m in mems:
                new_mem = self.db.memories.create(
                    session_id=new_sess.id,
                    kind=m.kind,
                    content=m.content,
                    priority=m.priority,
                    tags=m.tags_list(),
                    fictional_time=m.fictional_time,
                )
                if vs:
                    try:
                        vs.upsert_memory(
                            new_sess.id,
                            new_mem.id,
                            new_mem.content,
                            new_mem.kind,
                            new_mem.tags_list(),
                            new_mem.priority,
                        )
                    except Exception as e:
                        logger.error(f"Failed to re-index memory {new_mem.id}: {e}")

            # 4. Clone & Re-Index Turn Metadata
            turns = self.db.turn_metadata.get_all(session.id)
            for t in turns:
                new_turn_id = self.db.turn_metadata.create(
                    session_id=new_sess.id,
                    prompt_id=session.prompt_id,
                    round_number=t["round_number"],
                    summary=t["summary"],
                    tags=t["tags"],
                    importance=t["importance"],
                )

                if vs:
                    try:
                        vs.add_turn(
                            new_sess.id,
                            session.prompt_id,
                            t["round_number"],
                            t["summary"],
                            t["tags"],
                            t["importance"],
                        )
                    except Exception as e:
                        logger.error(f"Failed to re-index turn {new_turn_id}: {e}")

            ui.notify(f"Cloned to '{new_name}'")
            self.refresh()

        except Exception as e:
            ui.notify(f"Clone failed: {e}", type="negative")
            logger.error(f"Clone failed: {e}", exc_info=True)

    def confirm_delete(self, session):
        """Prepare and open the persistent delete dialog for this session."""
        self._session_to_delete = session
        if self.delete_dialog_label:
            self.delete_dialog_label.set_text(f"Delete '{session.name}'?")
        if self.delete_dialog:
            self.delete_dialog.open()

    def _execute_delete_session(self):
        """Called when the user confirms deletion in the dialog."""
        import logging

        logger = logging.getLogger(__name__)

        session = self._session_to_delete
        if not session:
            if self.delete_dialog:
                self.delete_dialog.close()
            return

        # 1. Delete SQL Data
        self.db.sessions.delete(session.id)

        # 2. Delete Vector Data
        vs = self.orchestrator.vector_store
        if vs:
            try:
                vs.delete_session_data(session.id)
            except Exception as e:
                logger.warning(
                    f"Failed to delete vector data for session {session.id}: {e}"
                )

        # If this was the active session, clear it and the chat view
        active = self.session_list.get_active_session()
        if active and active.id == session.id:
            self.session_list._active_session = None
            if self.session_list.chat_component:
                self.session_list.chat_component.container.clear()

        # Reset state and close dialog
        self._session_to_delete = None
        if self.delete_dialog:
            self.delete_dialog.close()

        self.refresh()
        ui.notify(f"Deleted {session.name}")
