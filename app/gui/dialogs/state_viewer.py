from nicegui import ui

class StateViewerDialog:
    def __init__(self, db_manager, session_id):
        self.db = db_manager
        self.session_id = session_id
        self.dialog = ui.dialog()
        self.json_editor = None

    def open(self):
        with self.dialog, ui.card().classes('w-[90%] h-[90%] bg-slate-950 border border-slate-700'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label("Raw State Viewer").classes('text-xl font-mono text-green-400')
                with ui.row():
                    ui.button("Refresh", icon='refresh', on_click=self.refresh).props('flat dense')
                    ui.button(icon='close', on_click=self.dialog.close).props('flat dense round')

            # State Data
            state_data = self._get_full_state()
            
            # Using ui.json_editor for nice tree view
            self.json_editor = ui.json_editor({'content': {'json': state_data}}) \
                .classes('w-full flex-grow')
        
        self.dialog.open()

    def _get_full_state(self):
        raw_state = self.db.game_state.get_all(self.session_id)
        # Simplify structure for viewing: { type: { key: data } }
        clean = {}
        for etype, items in raw_state.items():
            clean[etype] = {}
            for key, val in items.items():
                clean[etype][key] = val.get('data')
        return clean

    def refresh(self):
        if self.json_editor:
            data = self._get_full_state()
            self.json_editor.run_editor_method('update', {'json': data})
            ui.notify("State Refreshed")