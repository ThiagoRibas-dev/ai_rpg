from nicegui import ui
from app.gui.components.context_editor import ContextEditor
from app.gui.dialogs.lore_editor import LoreEditorDialog
import logging

logger = logging.getLogger(__name__)


class SessionListComponent:
    def __init__(self, db_manager, inspector_ref, orchestrator_ref):
        self.db = db_manager
        self.inspector = inspector_ref
        self.orchestrator = orchestrator_ref
        self._active_session = None
        self.container = None
        self.chat_component = None
        self.map_component = None

        # Sub-components
        self.context_editor = ContextEditor(db_manager)

    def set_chat_component(self, chat):
        self.chat_component = chat

    def set_map_component(self, map_cmp):
        self.map_component = map_cmp

    def get_active_session(self):
        return self._active_session

    def render(self):
        self.container = ui.column().classes("w-full gap-2")
        self.refresh()

        # Persistent Context Editor below the list
        self.context_editor.render()

        # Lorebook Button
        ui.button("Manage Lorebook", icon="book", on_click=self.open_lorebook).classes(
            "w-full mt-2 bg-purple-900/50 border border-purple-700 hover:bg-purple-900"
        )

    def refresh(self):
        self.container.clear()
        sessions = self.db.sessions.get_all()

        with self.container:
            if not sessions:
                ui.label("No Sessions").classes("text-gray-500")
                return

            for sess in sessions:
                bg = (
                    "bg-slate-700"
                    if self._active_session and self._active_session.id == sess.id
                    else "bg-slate-800"
                )

                with ui.row().classes(
                    f"w-full p-2 rounded cursor-pointer {bg} items-center justify-between group"
                ):
                    # Clickable Area
                    with (
                        ui.row()
                        .classes("flex-grow items-center gap-2")
                        .on("click", lambda s=sess: self.load_session(s))
                    ):
                        ui.icon("description").classes("text-gray-500")
                        with ui.column().classes("gap-0"):
                            ui.label(sess.name).classes("font-bold text-sm")
                            ui.label(sess.game_time).classes("text-xs text-gray-400")

                    # Context Menu for Actions
                    with (
                        ui.button(icon="more_vert")
                        .props("flat dense round size=sm")
                        .classes("text-gray-400 opacity-0 group-hover:opacity-100")
                    ):
                        with ui.menu():
                            ui.menu_item(
                                "Load", on_click=lambda s=sess: self.load_session(s)
                            )
                            ui.menu_item(
                                "Rename", on_click=lambda s=sess: self.rename_session(s)
                            )
                            ui.menu_item(
                                "Clone", on_click=lambda s=sess: self.clone_session(s)
                            )
                            ui.separator()
                            ui.menu_item(
                                "Delete", on_click=lambda s=sess: self.confirm_delete(s)
                            ).classes("text-red-400")

    def load_session(self, session):
        self._active_session = session
        self.orchestrator.load_game(session.id)

        if self.inspector:
            self.inspector.set_session(session.id)
        if self.chat_component:
            self.chat_component.load_history()

        # Update Map & Context Editor
        if self.map_component:
            self.map_component.set_session(session.id)
        self.context_editor.set_session(session.id)

        self.refresh()
        ui.notify(f"Loaded: {session.name}")

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
        # Create a copy
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
                    # val is {'data': ..., 'version': ...}
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
                # Re-Index into ChromaDB
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

            # 4. Clone & Re-Index Turn Metadata (History Search)
            turns = self.db.turn_metadata.get_all(session.id)
            for t in turns:
                # 't' is a dict from get_all
                new_turn_id = self.db.turn_metadata.create(
                    session_id=new_sess.id,
                    prompt_id=session.prompt_id,
                    round_number=t["round_number"],
                    summary=t["summary"],
                    tags=t[
                        "tags"
                    ],  # get_all returns list/dict, create handles json dump
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
        with ui.dialog() as dialog, ui.card():
            ui.label(f"Delete '{session.name}'?")
            with ui.row():
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button(
                    "Delete", on_click=lambda: self._delete_action(session, dialog)
                ).classes("bg-red-600")
        dialog.open()

    def _delete_action(self, session, dialog):
        # 1. Delete SQL Data (Cascades usually handle state, but let's be safe)
        self.db.sessions.delete(session.id)

        # 2. Delete Vector Data
        if self.orchestrator.vector_store:
            # We need to implement delete_session_data in vector_store if not present
            # But typically we leave it or have a method.
            # Assuming delete_session_data exists or is stubbed.
            try:
                self.orchestrator.vector_store.delete_session_data(session.id)
            except Exception as e:
                logger.warn(f"Failed to delete vector data for session {session.id}: {e}")
                pass

        if self._active_session and self._active_session.id == session.id:
            self._active_session = None
            if self.chat_component:
                self.chat_component.container.clear()

        dialog.close()
        self.refresh()
        ui.notify(f"Deleted {session.name}")

    def open_lorebook(self):
        if not self._active_session:
            ui.notify("Load a session first!", type="warning")
            return

        dialog = LoreEditorDialog(self.db, self._active_session.id)
        dialog.open()
