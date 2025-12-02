
from nicegui import ui
from app.gui.theme import Theme
from app.services.state_service import get_entity

class InventoryInspector:
    def __init__(self, db_manager, orchestrator):
        self.db = db_manager
        self.orchestrator = orchestrator
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
                                    ui.menu_item('Use/Equip', on_click=lambda i=item: self.trigger_action("use", i['name']))
                                    ui.menu_item('Drop', on_click=lambda i=item: self.trigger_action("drop", i['name']))
                                    ui.menu_item('Inspect', on_click=lambda i=item: self.trigger_action("inspect", i['name']))

    def trigger_action(self, verb: str, item_name: str):
        """
        Constructs a natural language command and sends it to the Orchestrator.
        """
        if not self.session_id or not self.orchestrator:
            ui.notify("Game engine not ready", type='negative')
            return

        # 1. Fetch the GameSession object (required by orchestrator)
        game_session = self.db.sessions.get_by_id(self.session_id)
        if not game_session:
            ui.notify("Session data error", type='negative')
            return

        # 2. Construct Input
        # "I use the Potion." / "I drop the Sword."
        command = f"I {verb} the {item_name}."
        
        # 3. Inject into Bridge (Simulate typing)
        # This ensures the chat UI updates and the orchestrator picks it up
        self.orchestrator.bridge._last_input = command
        
        # 4. Trigger Turn
        # Use a background task or notify the UI to start loading
        ui.notify(f"Action: {command}")
        
        # Signal the Chat Component to show 'Generating...' state
        if self.orchestrator.bridge.chat_component:
            self.orchestrator.bridge.chat_component.set_generating(True)
            self.orchestrator.bridge.chat_component.add_message("You", command, "user")

        # Execute
        self.orchestrator.plan_and_execute(game_session)
