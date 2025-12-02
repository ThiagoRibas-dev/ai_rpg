from nicegui import ui
from app.gui.theme import Theme

class MemoryInspector:
    def __init__(self, db_manager):
        self.db = db_manager
        self.session_id = None
        self.container = None
        self.search_term = ""

    def set_session(self, session_id: int):
        self.session_id = session_id
        self.refresh()

    def refresh(self):
        if not self.container:
            return
        self.container.clear()
        
        if not self.session_id:
            return

        # Fetch all (optimization: limit 50 usually)
        memories = self.db.memories.query(
            self.session_id, 
            query_text=self.search_term if self.search_term else None,
            limit=50
        )

        with self.container:
            # Search Bar
            ui.input(placeholder='Search Lore...', on_change=self._on_search) \
                .props('outlined dense rounded debounce=300') \
                .classes('w-full mb-2 bg-slate-800 text-white')

            with ui.scroll_area().classes('h-[600px] w-full pr-2'):
                if not memories:
                    ui.label("No memories found.").classes('text-gray-500 text-sm')
                
                for mem in memories:
                    self._render_memory_card(mem)

    def _on_search(self, e):
        self.search_term = e.value
        self.refresh()

    def _render_memory_card(self, mem):
        # Color coding tags
        kind_colors = {
            'episodic': 'blue-900',
            'semantic': 'green-900',
            'lore': 'purple-900',
            'user_pref': 'orange-900'
        }
        bg = kind_colors.get(mem.kind, 'slate-800')
        
        with ui.card().classes(f'w-full bg-slate-800 p-2 mb-2 border border-slate-700'):
            with ui.row().classes('w-full justify-between items-center mb-1'):
                ui.badge(mem.kind.upper(), color=bg).classes('text-[10px]')
                ui.label('★' * mem.priority).classes('text-yellow-500 text-xs')
            
            ui.markdown(mem.content).classes('text-sm text-gray-300 leading-tight')
            
            # Tags
            if mem.tags_list():
                with ui.row().classes('gap-1 mt-2 flex-wrap'):
                    for tag in mem.tags_list():
                        ui.label(f"#{tag}").classes('text-[10px] text-gray-500 bg-slate-900 px-1 rounded')