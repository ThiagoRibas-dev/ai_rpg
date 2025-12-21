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

        # --- Large Map Dialog (centered overlay) ---
        map_dialog = ui.dialog()

        def open_large_map():
            """Open the big map dialog, refreshing map data if a game is active."""
            try:
                active_session = session_list.get_active_session()
                if active_session:
                    map_comp.set_session(active_session.id)
                elif app.orchestrator.session and app.orchestrator.session.id:
                    map_comp.set_session(app.orchestrator.session.id)
                else:
                    # fallback: just let MapComponent pull whatever it can
                    map_comp.refresh_from_db()
            except Exception as e:
                logger.warning(f"Failed to refresh map before opening: {e}")
            map_dialog.open()

        with (
            map_dialog,
            ui.card().classes(
                "w-[90%] h-[90%] bg-slate-950 border border-slate-700 p-0"
            ),
        ):
            with ui.row().classes(
                "w-full items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-900"
            ):
                ui.label("Map").classes("text-sm font-bold text-gray-300")
                ui.button(icon="close", on_click=map_dialog.close).props(
                    "flat dense round"
                )
            with ui.column().classes("w-full h-full"):
                # Reuse existing MapComponent UI for the large view
                map_comp.render()

        # --- Layout ---

        # Header
        with Theme.header():
            ui.label("Generative Text RPG").classes(
                "text-xl font-bold " + Theme.text_accent
            )
            ui.space()

            # Header Labels (session, time, mode)
            with ui.row().classes("gap-4 text-xs text-gray-400"):
                sess_lbl = ui.label("No Session")
                time_lbl = ui.label("")
                mode_lbl = ui.label("")
                app.bridge.register_header_labels(sess_lbl, time_lbl, mode_lbl)

            ui.space()

            # Zen Mode Button (toggle_zen defined below)
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
                t_game = ui.tab("Game")
                t_chats = ui.tab("Chats")

            # Default to Chats when the app starts; we'll switch to Game on load
            with ui.tab_panels(tabs, value=t_chats).classes(
                "w-full bg-transparent p-0"
            ):
                # --- GAME TAB: mini scene, notes, lorebook, debug ---
                with ui.tab_panel(t_game):
                    with ui.column().classes("w-full p-2 gap-3"):
                        # Scene / mini-map section (textual overview + Open Map)
                        with ui.card().classes(
                            "w-full bg-slate-900 border border-slate-800 rounded"
                        ):
                            with ui.row().classes(
                                "w-full items-center justify-between mb-1"
                            ):
                                with ui.row().classes("items-center gap-2"):
                                    ui.icon("map").classes("text-gray-400")
                                    ui.label("Scene Overview").classes(
                                        "text-xs font-bold text-gray-300 uppercase"
                                    )
                                ui.button(
                                    "Open Map",
                                    icon="map",
                                    on_click=open_large_map,
                                ).props("flat dense").classes(
                                    "text-amber-400 hover:text-amber-300"
                                )

                            # Labels updated when a session is loaded
                            mini_session_lbl = ui.label("No game loaded").classes(
                                "text-sm text-gray-300"
                            )
                            mini_location_lbl = ui.label("Location: -").classes(
                                "text-xs text-gray-500"
                            )

                        # Author's Note editor (existing component)
                        session_list.context_editor.render()

                        # Lorebook & Debug tools
                        with ui.row().classes(
                            "w-full mt-2 items-center justify-between"
                        ):
                            ui.button(
                                "Manage Lorebook",
                                icon="book",
                                on_click=session_list.open_lorebook,
                            ).classes(
                                "flex-grow bg-purple-900/50 border border-purple-700 "
                                "hover:bg-purple-900 text-xs"
                            )

                # --- CHATS TAB: systems & saves management ---
                with ui.tab_panel(t_chats):
                    prompt_list.render()

            # Wire Game tab labels & tab control into SessionListComponent
            session_list.game_session_label = mini_session_lbl
            session_list.game_location_label = mini_location_lbl
            session_list.tabs = tabs
            session_list.game_tab = t_game
            session_list.chats_tab = t_chats

        # Zen Mode Logic (used by header button)
        def toggle_zen():
            current = left_drawer.value
            left_drawer.set_value(not current)
            right_drawer.set_value(not current)

        # Center Column: chat is primary; big map is via dialog only
        with ui.column().classes("w-full h-[calc(100vh-4rem)] p-0 gap-0 relative"):
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
