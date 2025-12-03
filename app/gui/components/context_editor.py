from nicegui import ui


class ContextEditor:
    def __init__(self, db_manager):
        self.db = db_manager
        self.session_id = None
        self.container = None
        self.text_area = None
        self.status_label = None

    def set_session(self, session_id: int):
        self.session_id = session_id
        self.refresh()

    def refresh(self):
        if not self.text_area or not self.session_id:
            return

        # Fetch current note
        sess = self.db.sessions.get_by_id(self.session_id)
        if sess:
            self.text_area.value = sess.authors_note or ""

    def save(self):
        if not self.session_id:
            return

        new_note = self.text_area.value
        self.db.sessions.update_context(self.session_id, "", new_note)

        # Visual feedback
        self.status_label.text = "Saved!"
        ui.timer(2.0, lambda: self.status_label.set_text(""))

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
