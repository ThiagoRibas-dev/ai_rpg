
from nicegui import ui
from app.gui.theme import Theme

# Import Sub-Inspectors
from app.gui.inspectors.character import CharacterInspector
from app.gui.inspectors.inventory import InventoryInspector
from app.gui.inspectors.quests import QuestInspector
from app.gui.inspectors.memory import MemoryInspector
from app.gui.dialogs.state_viewer import StateViewerDialog

class InspectorManager:
    """
    Manages the Left Drawer Tabs and delegates refresh calls to the active inspector.
    """
    def __init__(self, db_manager, orchestrator):
        self.db = db_manager
        self.orchestrator = orchestrator
        self.active_session_id = None
        
        # Instantiate sub-components
        self.char_view = CharacterInspector(db_manager)
        self.inv_view = InventoryInspector(db_manager, orchestrator) # Pass Orchestrator
        self.quest_view = QuestInspector(db_manager)
        self.mem_view = MemoryInspector(db_manager)

    def set_session(self, session_id: int):
        self.active_session_id = session_id
        # Propagate to all
        self.char_view.set_session(session_id)
        self.inv_view.set_session(session_id)
        self.quest_view.set_session(session_id)
        self.mem_view.set_session(session_id)

    def refresh(self):
        """Called by Bridge when game state changes."""
        if not self.active_session_id:
            return
            
        self.char_view.refresh()
        self.inv_view.refresh()
        self.quest_view.refresh()
        self.mem_view.refresh()

    def render(self):
        """Draws the Tab container and panels."""
        with ui.column().classes('w-full h-full p-0 gap-0'):
            
            # Tab Header
            with ui.tabs().classes('w-full text-gray-400 bg-slate-950') as tabs:
                t_char = ui.tab('Stats', icon='person')
                t_inv = ui.tab('Gear', icon='backpack')
                t_quest = ui.tab('Quest', icon='map')
                t_mem = ui.tab('Lore', icon='history')

            # Tab Content (Fill remaining height)
            with ui.tab_panels(tabs, value=t_char).classes('w-full flex-grow bg-transparent p-2'):
                
                with ui.tab_panel(t_char).classes('p-0'):
                    self.char_view.render()
                    
                with ui.tab_panel(t_inv).classes('p-0'):
                    self.inv_view.container = ui.column().classes('w-full')
                    self.inv_view.refresh() 
                    
                with ui.tab_panel(t_quest).classes('p-0'):
                    self.quest_view.container = ui.column().classes('w-full')
                    self.quest_view.refresh()
                    
                with ui.tab_panel(t_mem).classes('p-0'):
                    self.mem_view.container = ui.column().classes('w-full')
                    self.mem_view.refresh()

            # Footer / Debug
            with ui.row().classes('w-full p-2 border-t border-slate-800 justify-center'):
                ui.button("Debug State", icon='bug_report', on_click=self.open_debug) \
                    .props('flat dense text-color=grey')

    def open_debug(self):
        if not self.active_session_id: 
            ui.notify("No Session")
            return
        
        dialog = StateViewerDialog(self.db, self.active_session_id)
        dialog.open()
