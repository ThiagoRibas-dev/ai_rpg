import json
from nicegui import ui
from app.gui.theme import Theme


class ChatComponent:
    def __init__(self, orchestrator, bridge, session_manager):
        self.orchestrator = orchestrator
        self.bridge = bridge
        self.session_manager = session_manager

        # UI References
        self.container = None
        self.input_area = None
        self.scroll_area = None
        self.nav_container = None
        self.send_btn = None
        self.stop_btn = None

        self.bridge.register_chat(self)

    def render(self):
        # Message Area
        with ui.scroll_area().classes("w-full flex-grow p-4 gap-4") as area:
            self.container = ui.column().classes("w-full gap-4")
            self.scroll_area = area

            with self.container:
                self.add_system_message("Ready. Load a session to begin.")

        # Input Area Wrapper
        with ui.column().classes("w-full p-0 gap-0 border-t border-slate-700"):
            # Navigation Bar
            self.nav_container = ui.row().classes(
                "w-full justify-center gap-2 p-2 bg-slate-900 border-b border-slate-800"
            )
            self.nav_container.set_visibility(False)

            # Input Row
            with ui.row().classes(
                "w-full p-4 " + Theme.bg_tertiary + " items-end gap-2 flex-nowrap"
            ):
                # Global History Menu
                with (
                    ui.button(icon="history")
                    .props("flat round dense")
                    .classes("text-gray-400")
                ):
                    with ui.menu():
                        ui.menu_item("Reload History", on_click=self.load_history)
                        ui.separator()
                        ui.menu_item(
                            "Clear Chat View", on_click=lambda: self.container.clear()
                        )

                self.input_area = (
                    ui.textarea(placeholder="What do you do?")
                    .props('autogrow rows=1 rounded outlined input-class="text-white"')
                    .classes("flex-grow text-lg")
                    # Ctrl+Enter submits, prevents newline
                    .on("keydown.ctrl.enter.prevent", self.handle_enter)
                )

                # Send Button
                self.send_btn = (
                    ui.button(icon="send", on_click=self.handle_enter)
                    .props("flat round dense")
                    .classes(Theme.text_accent)
                )

                # Stop Button
                self.stop_btn = (
                    ui.button(icon="stop", on_click=self.handle_stop)
                    .props("flat round dense")
                    .classes("text-red-500")
                )
                self.stop_btn.set_visibility(False)

    def set_generating(self, is_generating: bool):
        """Toggles the input state based on generation status."""
        if self.send_btn and self.stop_btn:
            self.send_btn.set_visibility(not is_generating)
            self.stop_btn.set_visibility(is_generating)

        if self.input_area:
            if is_generating:
                self.input_area.disable()
            else:
                self.input_area.enable()
                self.input_area.run_method("focus")

    def load_history(self):
        if not self.container:
            return
        self.container.clear()

        session = self.orchestrator.session
        if not session:
            return

        with self.container:
            for index, msg in enumerate(session.history):
                if msg.role == "tool":
                    continue

                if msg.role == "user":
                    name = "Player"
                elif msg.role == "assistant":
                    name = "Game Master"
                elif msg.role == "system":
                    name = "System"
                else:
                    name = msg.role.capitalize()

                self._render_interactive_message(index, msg, name)

        self._scroll_down()

    def _render_interactive_message(self, index: int, msg, name: str):
        sent = msg.role == "user"

        if msg.role == "thought":
            with ui.row().classes("w-full justify-start"):
                with ui.card().classes(
                    "bg-yellow-900/20 border border-yellow-700/50 p-2 w-full max-w-3xl"
                ):
                    ui.label("💭 Thinking...").classes(
                        "text-xs text-yellow-500 font-bold mb-1"
                    )
                    ui.markdown(msg.content).classes("text-sm text-yellow-200 italic")
            return

        if msg.role == "system":
            self.add_system_message(msg.content)
            return

        chat_msg = ui.chat_message(name=name, sent=sent)

        with chat_msg:
            with ui.context_menu():
                ui.menu_item(
                    "Edit",
                    on_click=lambda: self._toggle_edit_mode(
                        content_container, index, msg
                    ),
                )
                ui.menu_item(
                    "Delete", on_click=lambda: self._delete_message(index)
                ).classes("text-red-400")
                if not sent:
                    ui.separator()
                    ui.menu_item(
                        "Regenerate from here",
                        on_click=lambda: self._regenerate_from(index),
                    )

            content_container = ui.column().classes(
                "w-full p-0 m-0 gap-2 min-w-[200px]"
            )
            with content_container:
                ui.markdown(msg.content).classes("text-base leading-relaxed")
                with ui.row().classes(
                    "opacity-0 hover:opacity-100 transition-opacity absolute -right-2 -top-2 bg-slate-800 rounded-full shadow-sm"
                ):
                    ui.button(
                        icon="edit",
                        on_click=lambda: self._toggle_edit_mode(
                            content_container, index, msg
                        ),
                    ).props("flat dense round size=xs")

    def _toggle_edit_mode(self, container, index, msg):
        container.clear()
        with container:
            editor = (
                ui.textarea(value=msg.content)
                .classes("w-full min-w-[300px] bg-slate-900 p-2 rounded")
                .props('autogrow input-class="text-sm"')
            )
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=lambda: self.load_history()).props(
                    "flat dense size=sm"
                )
                ui.button(
                    "Save", on_click=lambda: self._save_edit(index, editor.value)
                ).classes("bg-green-600 text-white").props("dense size=sm")

    def _save_edit(self, index, new_content):
        session = self.orchestrator.session
        if 0 <= index < len(session.history):
            session.history[index].content = new_content
            game_session = self.session_manager.get_active_session()
            if game_session:
                game_session.session_data = session.to_json()
                self.session_manager.db.sessions.update(game_session)
                ui.notify("Message updated")
            self.load_history()

    def _delete_message(self, index):
        session = self.orchestrator.session
        if 0 <= index < len(session.history):
            session.history.pop(index)
            game_session = self.session_manager.get_active_session()
            if game_session:
                game_session.session_data = session.to_json()
                self.session_manager.db.sessions.update(game_session)
                ui.notify("Message deleted")
            self.load_history()

    def _regenerate_from(self, index):
        session = self.orchestrator.session
        if 0 <= index < len(session.history):
            target_msg = session.history[index]
            if target_msg.role == "assistant":
                session.history = session.history[:index]
            elif target_msg.role == "user":
                session.history = session.history[: index + 1]

            game_session = self.session_manager.get_active_session()
            if game_session:
                game_session.session_data = session.to_json()
                self.session_manager.db.sessions.update(game_session)

                # Reset stop flag and set new turn ID
                self.set_generating(True)
                import threading
                import uuid

                new_turn_id = uuid.uuid4().hex
                self.orchestrator.active_turn_id = new_turn_id
                self.orchestrator.bridge.set_active_turn(new_turn_id)

                last_user_msg = ""
                if session.history and session.history[-1].role == "user":
                    last_user_msg = session.history[-1].content

                if last_user_msg:
                    thread = threading.Thread(
                        target=self.orchestrator._background_execute,
                        args=(game_session, last_user_msg, new_turn_id),
                        daemon=True,
                    )
                    thread.start()

            self.load_history()

    def add_message(self, name: str, text: str, role: str):
        if not self.container:
            return
        with self.container:
            sent = role == "user"
            if role == "thought":
                with ui.row().classes("w-full justify-start"):
                    with ui.card().classes(
                        "bg-yellow-900/20 border border-yellow-700/50 p-2"
                    ):
                        ui.label("💭 Thinking...").classes(
                            "text-xs text-yellow-500 font-bold mb-1"
                        )
                        ui.markdown(text).classes("text-sm text-yellow-200 italic")
            else:
                with ui.chat_message(name=name, sent=sent):
                    ui.markdown(text).classes("text-base leading-relaxed")
        self._scroll_down()

    def add_system_message(self, text):
        if not self.container:
            return
        with self.container:
            with ui.row().classes("w-full justify-center my-2"):
                ui.label(text).classes(
                    "text-gray-500 italic text-xs bg-slate-900 px-3 py-1 rounded-full"
                )
        self._scroll_down()

    def add_location_banner(self, location_data: dict):
        if not self.container:
            return
        name = location_data.get("name", "Unknown Location")
        desc = location_data.get("description_visual", "")
        with self.container:
            with ui.row().classes("w-full justify-center"):
                with ui.card().classes(
                    "w-full max-w-2xl bg-slate-950 border-y-2 border-amber-600 p-4 items-center text-center"
                ):
                    ui.label(f"📍 {name}").classes(
                        "text-xl font-bold text-amber-500 uppercase tracking-widest"
                    )
                    if desc:
                        ui.label(desc).classes(
                            "text-sm text-gray-400 italic mt-2 font-serif"
                        )
        self._scroll_down()

    def update_navigation(self, exits: list):
        if not self.nav_container:
            return
        self.nav_container.clear()
        if not exits:
            self.nav_container.set_visibility(False)
            return
        self.nav_container.set_visibility(True)
        with self.nav_container:
            ui.label("EXITS:").classes(
                "text-xs font-bold text-gray-500 self-center mr-2"
            )
            for direction in exits:
                ui.button(
                    direction.title(),
                    on_click=lambda d=direction: self.handle_choice(f"Go {d}"),
                ).props("outline dense size=sm").classes(
                    "text-gray-300 border-gray-600 hover:bg-slate-800"
                )

    def clear_navigation(self):
        if self.nav_container:
            self.nav_container.clear()
            self.nav_container.set_visibility(False)

    def add_tool_log(self, name: str, args: dict):
        if not self.container:
            return
        with self.container:
            with ui.row().classes("w-full justify-start"):
                with ui.expansion(f"🛠 {name}", icon="code").classes(
                    "w-full max-w-lg bg-slate-900 border border-slate-800 rounded text-xs"
                ):
                    # Adds the tool args to the chat as a read only JSON for better readability:
                    ui.code(json.dumps(args, indent=2)).classes("text-xs text-gray-400")
        self._scroll_down()

    def add_dice_roll(self, spec: str, total: int, rolls: list):
        if not self.container:
            return
        is_crit = total >= 20
        is_fail = total == 1
        border = "border-slate-600"
        text_col = "text-white"
        if is_crit:
            border = "border-green-500 shadow-lg shadow-green-900/50"
            text_col = "text-green-400"
        elif is_fail:
            border = "border-red-500"
            text_col = "text-red-400"
        with self.container:
            with ui.row().classes("w-full justify-center"):
                with ui.card().classes(
                    f"bg-slate-800 {border} border-2 p-4 items-center min-w-[200px]"
                ):
                    ui.label(f"Rolled {spec}").classes(
                        "text-xs text-gray-400 uppercase font-bold"
                    )
                    ui.label(str(total)).classes(f"text-4xl font-black {text_col}")
                    if len(rolls) > 1:
                        ui.label(f"Results: {rolls}").classes("text-xs text-gray-500")
        self._scroll_down()

    def add_choices(self, choices: list):
        if not self.container or not choices:
            return
        with self.container:
            with ui.column().classes(
                "w-full items-center gap-2 p-4 bg-slate-900/50 rounded border border-slate-700"
            ):
                ui.label("Suggested Actions").classes(
                    "text-xs font-bold text-gray-500 uppercase"
                )
                with ui.row().classes("flex-wrap justify-center gap-2"):
                    for choice in choices:
                        ui.button(
                            choice, on_click=lambda c=choice: self.handle_choice(c)
                        ).classes("bg-slate-700 hover:bg-slate-600 text-white text-sm")
        self._scroll_down()

    def handle_choice(self, text):
        self.input_area.value = text
        self.handle_enter()

    def handle_enter(self):
        text = self.input_area.value
        if not text.strip():
            return

        self.input_area.value = ""

        # FIX: Do NOT add message here. The Orchestrator adds it to the queue via plan_and_execute.
        # self.add_message("You", text, "user")

        self.bridge._last_input = text

        self.set_generating(True)

        if self.orchestrator.session:
            game_session = self.session_manager.get_active_session()
            if game_session:
                self.orchestrator.plan_and_execute(game_session)
            else:
                ui.notify("Session state mismatch", type="negative")
                self.set_generating(False)
        else:
            ui.notify("No session loaded!", type="warning")
            self.set_generating(False)

    def handle_stop(self):
        self.orchestrator.stop_generation()
        self.set_generating(False)
        ui.notify("Stopping AI...")

    def _scroll_down(self):
        if self.scroll_area:
            self.scroll_area.scroll_to(percent=1.0)
