from nicegui import ui, app
import logging
from app.gui.theme import Theme
from app.database.db_manager import DBManager
from app.core.orchestrator import Orchestrator
from app.gui.bridge import NiceGUIBridge
from app.services.manifest_service import seed_builtin_manifests

# Components
from app.gui.components.chat import ChatComponent
from app.gui.components.map import MapComponent
from app.gui.inspectors.manager import InspectorManager
from app.gui.controls.session_list import SessionListComponent
from app.gui.controls.prompt_list import PromptListComponent

logger = logging.getLogger(__name__)


def init_gui(db_path: str):
    # 1. Initialize DB & Seed Manifests
    app.db_manager = DBManager(db_path)

    # EXPLICITLY OPEN CONNECTION for the lifecycle of the app
    # This prevents create_tables() from opening/closing it via context manager
    app.db_manager.__enter__()

    app.db_manager.create_tables()
    seed_builtin_manifests(db_path)

    # 2. Init Core Systems
    app.bridge = NiceGUIBridge()
    app.orchestrator = Orchestrator(app.bridge, db_path)

    @ui.page("/")
    def main_page():
        Theme.apply_global_styles()

        # --- Init Components ---
        inspector_mgr = InspectorManager(app.db_manager, app.orchestrator)
        app.bridge.register_inspector(inspector_mgr)

        session_list = SessionListComponent(
            app.db_manager, inspector_mgr, app.orchestrator
        )
        prompt_list = PromptListComponent(
            app.db_manager, app.orchestrator, session_list
        )
        chat_comp = ChatComponent(app.orchestrator, app.bridge, session_list)

        map_comp = MapComponent(app.bridge, app.db_manager)
        session_list.set_map_component(map_comp)
        session_list.set_chat_component(chat_comp)

        # --- Layout ---

        # Header
        with Theme.header():
            ui.label("Generative Text RPG").classes(
                "text-xl font-bold " + Theme.text_accent
            )
            ui.space()

            # Header Labels
            with ui.row().classes("gap-4 text-xs text-gray-400"):
                sess_lbl = ui.label("No Session")
                time_lbl = ui.label("")
                mode_lbl = ui.label("")
                app.bridge.register_header_labels(sess_lbl, time_lbl, mode_lbl)

            ui.space()

            # Zen Mode Button
            ui.button(icon="fullscreen", on_click=lambda: toggle_zen()).props(
                "flat round dense"
            )
            ui.button(icon="power_settings_new", on_click=app.shutdown).props(
                "flat dense round color=red"
            )

        # Drawers
        left_drawer = Theme.drawer_left()
        with left_drawer:
            inspector_mgr.render()

        right_drawer = Theme.drawer_right()
        with right_drawer:
            with ui.tabs().classes("w-full text-gray-400") as tabs:
                t_sessions = ui.tab("Sessions")
                t_prompts = ui.tab("New Game")

            with ui.tab_panels(tabs, value=t_sessions).classes(
                "w-full bg-transparent p-0"
            ):
                with ui.tab_panel(t_sessions):
                    session_list.render()
                with ui.tab_panel(t_prompts):
                    prompt_list.render()

        # Zen Mode Logic
        def toggle_zen():
            current = left_drawer.value
            left_drawer.set_value(not current)
            right_drawer.set_value(not current)

        # Center Column
        with ui.column().classes("w-full h-[calc(100vh-4rem)] p-0 gap-0 relative"):
            # Splitter: value=30 means map takes 30% height by default
            with ui.splitter(value=30, horizontal=True).classes(
                "w-full h-full"
            ) as splitter:
                # Top Pane: Map
                with splitter.before:
                    with ui.column().classes("w-full h-full bg-slate-950 p-0 gap-0"):
                        map_comp.render()

                # Bottom Pane: Chat
                with splitter.after:
                    with ui.column().classes("w-full h-full bg-slate-900 p-0 gap-0"):
                        chat_comp.render()

        # Polling Loop
        ui.timer(0.1, app.bridge.process_queue)

    async def cleanup():
        print("🛑 Shutting down...")
        if hasattr(app, "db_manager") and app.db_manager.conn:
            app.db_manager.__exit__(None, None, None)

    app.on_shutdown(cleanup)


def run(db_path: str):
    init_gui(db_path)
    ui.run(
        title="AI RPG", dark=True, reload=False, native=True, window_size=(1600, 900)
    )
