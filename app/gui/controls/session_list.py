from nicegui import ui
from app.gui.theme import Theme

class SessionListComponent:
    def __init__(self, db_manager, inspector_ref, orchestrator_ref):
        self.db = db_manager
        self.inspector = inspector_ref
        self.orchestrator = orchestrator_ref
        self._active_session = None
        self.container = None
        self.chat_component = None
        self.map_component = None # New dependency

    def set_chat_component(self, chat): self.chat_component = chat
    def set_map_component(self, map_cmp): self.map_component = map_cmp

    def get_active_session(self): return self._active_session

    def render(self):
        self.container = ui.column().classes('w-full gap-2')
        self.refresh()

    def refresh(self):
        self.container.clear()
        sessions = self.db.sessions.get_all()
        
        with self.container:
            if not sessions:
                ui.label("No Sessions").classes('text-gray-500')
                return

            for sess in sessions:
                bg = 'bg-slate-700' if self._active_session and self._active_session.id == sess.id else 'bg-slate-800'
                with ui.row().classes(f'w-full p-2 rounded cursor-pointer {bg} items-center justify-between') \
                        .on('click', lambda s=sess: self.load_session(s)):
                    
                    with ui.column().classes('gap-0'):
                        ui.label(sess.name).classes('font-bold text-sm')
                        ui.label(sess.game_time).classes('text-xs text-gray-400')
                    ui.icon('chevron_right').classes('text-gray-500')

    def load_session(self, session):
        self._active_session = session
        self.orchestrator.load_game(session.id)
        
        if self.orchestrator.view and hasattr(self.orchestrator.view, 'session_name_label'):
            self.orchestrator.view.session_name_label.configure(text=session.name)

        if self.inspector: self.inspector.set_session(session.id)
        if self.chat_component: self.chat_component.load_history()
        
        # Refresh Map
        if self.map_component:
            self.map_component.set_session(session.id)
            
        self.refresh()
        ui.notify(f"Loaded: {session.name}")