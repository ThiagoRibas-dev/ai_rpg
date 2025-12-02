from nicegui import ui
from app.models.memory import Memory

class LoreEditorDialog:
    def __init__(self, db_manager, session_id):
        self.db = db_manager
        self.session_id = session_id
        self.dialog = ui.dialog()
        self.list_container = None
        self.edit_container = None
        self.selected_mem = None
        
        # Editor State
        self.edit_content = ""
        self.edit_tags = ""

    def open(self):
        with self.dialog, ui.card().classes('w-[900px] h-[700px] bg-slate-900 border border-slate-700 p-0'):
            # Header
            with ui.row().classes('w-full bg-slate-950 p-4 justify-between items-center border-b border-slate-800'):
                ui.label("Lorebook Editor").classes('text-xl font-bold text-amber-500')
                ui.button(icon='close', on_click=self.dialog.close).props('flat dense round')

            # Body (Split View)
            with ui.row().classes('w-full h-full gap-0'):
                # Left: List
                with ui.column().classes('w-1/3 h-full border-r border-slate-800 p-2'):
                    ui.button("New Entry", icon='add', on_click=self.create_new).classes('w-full bg-slate-800 mb-2')
                    with ui.scroll_area().classes('w-full flex-grow'):
                        self.list_container = ui.column().classes('w-full gap-1')
                
                # Right: Editor
                with ui.column().classes('w-2/3 h-full p-4 gap-4'):
                    self.edit_container = ui.column().classes('w-full h-full hidden')
                    with self.edit_container:
                        ui.label("Edit Entry").classes('text-lg font-bold text-gray-400')
                        ui.input(label="Tags").bind_value(self, 'edit_tags').classes('w-full')
                        ui.textarea(label="Content").bind_value(self, 'edit_content').classes('w-full flex-grow text-sm').props('outlined')
                        
                        with ui.row().classes('w-full justify-end'):
                            ui.button("Delete", on_click=self.delete_current, color='red').props('flat')
                            ui.button("Save Changes", on_click=self.save_current).classes('bg-green-600')

        self.refresh_list()
        self.dialog.open()

    def refresh_list(self):
        if not self.list_container: return
        self.list_container.clear()
        
        memories = self.db.memories.query(self.session_id, kind='lore', limit=100)
        
        with self.list_container:
            for mem in memories:
                # Truncate content for title
                title = (mem.content[:30] + '...') if len(mem.content) > 30 else mem.content
                bg = 'bg-slate-700' if self.selected_mem and self.selected_mem.id == mem.id else 'bg-transparent'
                
                ui.button(title, on_click=lambda m=mem: self.select_entry(m)) \
                    .classes(f'w-full text-left text-xs truncate {bg} hover:bg-slate-800 p-2 rounded')

    def select_entry(self, memory):
        self.selected_mem = memory
        self.edit_content = memory.content
        self.edit_tags = ", ".join(memory.tags_list())
        
        self.edit_container.classes(remove='hidden')
        self.refresh_list() # To update active highlight

    def create_new(self):
        new_mem = self.db.memories.create(
            session_id=self.session_id,
            kind='lore',
            content="New Entry",
            priority=3,
            tags=['new']
        )
        self.select_entry(new_mem)

    def save_current(self):
        if not self.selected_mem: return
        
        tags = [t.strip() for t in self.edit_tags.split(',') if t.strip()]
        
        updated = self.db.memories.update(
            self.selected_mem.id,
            content=self.edit_content,
            tags=tags
        )
        self.selected_mem = updated # Refresh ref
        self.refresh_list()
        ui.notify("Entry Saved")

    def delete_current(self):
        if not self.selected_mem: return
        self.db.memories.delete(self.selected_mem.id)
        self.selected_mem = None
        self.edit_container.classes(add='hidden')
        self.refresh_list()