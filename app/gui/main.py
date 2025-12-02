from nicegui import ui, app
import logging
from app.gui.theme import Theme
from app.database.db_manager import DBManager
from app.core.orchestrator import Orchestrator
from app.gui.bridge import NiceGUIBridge

# Components
from app.gui.components.chat import ChatComponent
from app.gui.components.map import MapComponent
from app.gui.inspectors.manager import InspectorManager
from app.gui.controls.session_list import SessionListComponent
from app.gui.controls.prompt_list import PromptListComponent

logger = logging.getLogger(__name__)

def init_gui(db_path: str):
    app.db_manager = DBManager(db_path)
    app.db_manager.__enter__() 
    app.db_manager.create_tables()
    app.bridge = NiceGUIBridge()
    app.orchestrator = Orchestrator(app.bridge, db_path)

    @ui.page('/')
    def main_page():
        Theme.apply_global_styles()
        
        # --- Init ---
        inspector_mgr = InspectorManager(app.db_manager)
        app.bridge.register_inspector(inspector_mgr)
        
        session_list = SessionListComponent(app.db_manager, inspector_mgr, app.orchestrator)
        prompt_list = PromptListComponent(app.db_manager, app.orchestrator, session_list)
        chat_comp = ChatComponent(app.orchestrator, app.bridge, session_list)
        
        # Map
        map_comp = MapComponent(app.bridge, app.db_manager)
        session_list.set_map_component(map_comp)
        
        session_list.set_chat_component(chat_comp)
        
        # --- Layout ---
        with Theme.header():
            ui.label('Generative Text RPG').classes('text-xl font-bold ' + Theme.text_accent)
            ui.space()
            session_label = ui.label('No Session Loaded').classes('text-xs text-gray-500')
            app.bridge.register_header_label(session_label)
            ui.button(icon='power_settings_new', on_click=app.shutdown).props('flat dense round color=red')

        with Theme.drawer_left():
            inspector_mgr.render()

        with Theme.drawer_right():
            with ui.tabs().classes('w-full text-gray-400') as tabs:
                t_sessions = ui.tab('Sessions')
                t_prompts = ui.tab('New Game')
            
            with ui.tab_panels(tabs, value=t_sessions).classes('w-full bg-transparent p-0'):
                with ui.tab_panel(t_sessions):
                    session_list.render()
                with ui.tab_panel(t_prompts):
                    prompt_list.render()

        # Center Column
        with ui.column().classes('w-full h-[calc(100vh-4rem)] p-0 gap-0'):
            
            # Map Section (Top 30% or expandable)
            # We wrap it in a collapsible or just a fixed box
            with ui.expansion('Tactical Map', icon='map').classes('w-full bg-slate-900 border-b border-slate-700'):
                map_comp.render()
            
            # Chat Section (Fills rest)
            chat_comp.render()

        ui.timer(0.1, app.bridge.process_queue)

    async def cleanup():
        print("🛑 Shutting down...")
        if app.db_manager.conn:
            app.db_manager.__exit__(None, None, None)
    app.on_shutdown(cleanup)

def run(db_path: str):
    init_gui(db_path)
    ui.run(title="AI RPG", dark=True, reload=False, native=True, window_size=(1600, 900))