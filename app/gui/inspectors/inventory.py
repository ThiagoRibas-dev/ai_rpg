from nicegui import ui
from app.gui.theme import Theme
from app.tools.builtin._state_storage import get_entity

class InventoryInspector:
    def __init__(self, db_manager):
        self.db = db_manager
        self.session_id = None
        self.container = None

    def set_session(self, session_id: int):
        self.session_id = session_id
        self.refresh()

    def refresh(self):
        if not self.container:
            return
        
        self.container.clear()
        
        if not self.session_id:
            with self.container:
                ui.label("No Session").classes('text-gray-500 italic')
            return

        entity = get_entity(self.session_id, self.db, "character", "player")
        if not entity:
            return

        # Fetch Template to know which collections exist
        tid = entity.get("template_id")
        template = self.db.stat_templates.get_by_id(tid) if tid else None
        
        collections_data = entity.get('collections', {})

        with self.container:
            # If we have a template, iterate through defined collections
            if template:
                for col_key, col_def in template.collections.items():
                    items = collections_data.get(col_key, [])
                    self._render_collection(col_def.label, items)
            else:
                # Fallback: Render raw dictionary keys
                for key, items in collections_data.items():
                    self._render_collection(key.capitalize(), items)

    def _render_collection(self, title, items):
        with ui.expansion(f"{title} ({len(items)})", icon='backpack').classes('w-full bg-slate-800 rounded mb-2').props('default-opened'):
            if not items:
                ui.label("Empty").classes('text-gray-500 italic text-sm p-2')
                return

            with ui.column().classes('w-full gap-1 p-2'):
                for item in items:
                    with ui.row().classes('w-full justify-between items-center bg-slate-900 p-2 rounded border border-slate-700'):
                        
                        # Left: Name & Details
                        with ui.column().classes('gap-0'):
                            ui.label(item.get('name', '???')).classes('font-bold text-gray-200')
                            
                            # Render extra fields if they exist (Weight, etc)
                            extras = [f"{k}: {v}" for k, v in item.items() if k not in ['name', 'qty', 'description']]
                            if extras:
                                ui.label(", ".join(extras)).classes('text-xs text-gray-500')

                        # Right: Quantity & Menu
                        with ui.row().classes('items-center'):
                            if item.get('qty', 1) > 1:
                                ui.badge(f"x{item['qty']}", color='blue-900')
                            
                            # Context Menu Button
                            with ui.button(icon='more_vert').props('flat dense round size=sm color=grey'):
                                with ui.menu():
                                    ui.menu_item('Use/Equip', on_click=lambda i=item: ui.notify(f"Used {i['name']}"))
                                    ui.menu_item('Drop', on_click=lambda: ui.notify("Drop not implemented"))