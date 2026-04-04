from __future__ import annotations

import typing

from nicegui import ui

if typing.TYPE_CHECKING:
    from app.database.db_manager import DBManager



class ContextEditor:
    text_area: ui.textarea | None
    status_label: ui.label | None

    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        self.session_id: int | None = None
        self.container: ui.column | None = None
        self.text_area = None
        self.status_label = None

    def set_session(self, session_id: int):
        self.session_id = session_id
        self.refresh()

    def refresh(self):
        if not self.text_area or not self.session_id:
            return

        # Fetch current note
        if not self.db.sessions:
            return
        sess = self.db.sessions.get_by_id(self.session_id)
        if sess and self.text_area:
            self.text_area.value = sess.authors_note or ""

    def save(self):
        if not self.session_id or not self.text_area or not self.status_label:
            return

        new_note = self.text_area.value
        if self.db.sessions:
            self.db.sessions.update_context(self.session_id, "", new_note)

        # Visual feedback
        self.status_label.text = "Saved!"

        def clear_status():
            if self.status_label:
                self.status_label.set_text("")

        ui.timer(2.0, clear_status, once=True)

    def render(self):
        with ui.column().classes("w-full gap-2 mt-4 border-t border-slate-700 pt-4"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.label("Author's Note").classes(
                    "text-sm font-bold text-gray-400 uppercase"
                )
                self.status_label = ui.label("").classes("text-xs text-green-400")

            ui.label("Instructions injected into every turn.").classes(
                "text-xs text-gray-600 italic"
            )

            self.text_area = (
                ui.textarea(placeholder="e.g. The NPCs should be suspicious...")
                .classes("w-full bg-slate-900 text-sm")
                .props('rows=5 rounded outlined input-class="text-gray-300"')
            )

            ui.button("Save Note", on_click=self.save).classes(
                "w-full bg-slate-700 hover:bg-slate-600 text-xs"
            )
