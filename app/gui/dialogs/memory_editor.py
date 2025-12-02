from nicegui import ui
from app.models.memory import Memory

class MemoryEditorDialog:
    def __init__(self, db_manager, memory: Memory, on_change=None):
        self.db = db_manager
        self.memory = memory
        self.on_change = on_change
        self.dialog = ui.dialog()
        
        # Bindable state
        self.kind = memory.kind
        self.content = memory.content
        self.priority = memory.priority
        self.tags_str = ", ".join(memory.tags_list())

    def open(self):
        with self.dialog, ui.card().classes('w-[600px] bg-slate-900 border border-slate-700'):
            ui.label(f"Edit Memory #{self.memory.id}").classes('text-lg font-bold text-white mb-4')
            
            # Form
            with ui.grid(columns=2).classes('w-full gap-4'):
                ui.select(['episodic', 'semantic', 'lore', 'user_pref'], label="Kind") \
                    .bind_value(self, 'kind').classes('w-full')
                
                ui.number(label="Priority (1-5)", min=1, max=5, format='%.0f') \
                    .bind_value(self, 'priority').classes('w-full')

            ui.input(label="Tags (comma separated)").bind_value(self, 'tags_str').classes('w-full')
            
            ui.textarea(label="Content").bind_value(self, 'content').classes('w-full').props('rows=6')

            # Actions
            with ui.row().classes('w-full justify-end mt-4 gap-2'):
                ui.button("Delete", on_click=self.delete, color='red').props('flat')
                ui.button("Cancel", on_click=self.dialog.close).props('flat')
                ui.button("Save", on_click=self.save)
        
        self.dialog.open()

    def save(self):
        tags_list = [t.strip() for t in self.tags_str.split(',') if t.strip()]
        
        self.db.memories.update(
            self.memory.id,
            kind=self.kind,
            content=self.content,
            priority=int(self.priority),
            tags=tags_list
        )
        
        ui.notify("Memory Updated")
        self.dialog.close()
        if self.on_change: self.on_change()

    def delete(self):
        self.db.memories.delete(self.memory.id)
        ui.notify("Memory Deleted")
        self.dialog.close()
        if self.on_change: self.on_change()