from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from nicegui import ui

from app.gui.theme import Theme

if TYPE_CHECKING:
    from app.core.orchestrator import Orchestrator
    from app.gui.bridge import NiceGUIBridge
    from app.gui.controls.session_list import SessionListComponent

from app.models.message import Message
from app.models.vocabulary import MessageRole


class ChatComponent:
    def __init__(self, orchestrator: Orchestrator, bridge: NiceGUIBridge, session_manager: SessionListComponent):
        self.orchestrator = orchestrator
        self.bridge = bridge
        self.session_manager = session_manager

        # UI References
        self.container: ui.column | None = None
        self.input_area: ui.textarea | None = None
        self.scroll_area: ui.scroll_area | None = None
        self.nav_container: ui.row | None = None
        self.send_btn: ui.button | None = None
        self.stop_btn: ui.button | None = None

        self.bridge.register_chat(self)

    def render(self):
        # Message Area
        with ui.scroll_area().classes("w-full flex-grow p-4 gap-4 overflow-x-hidden") as area:
            self.container = ui.column().classes("w-full gap-4 max-w-full")
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
        if not session or not session.history:
            return


        with self.container:
            for index, msg in enumerate(session.history):
                # We no longer skip TOOL messages, we render them!
                # if msg.role == MessageRole.TOOL:
                #     continue

                if msg.role == MessageRole.USER:
                    name = "Player"
                elif msg.role == MessageRole.ASSISTANT:
                    name = "Game Master"
                elif msg.role == MessageRole.SYSTEM:
                    name = "System"
                elif msg.role == MessageRole.TOOL:
                    name = f"Tool: {msg.name or 'Result'}"
                else:
                    name = str(msg.role).capitalize()

                self._render_interactive_message(index, msg, name)

        self._scroll_down()

    def _render_interactive_message(self, index: int, msg: Message, name: str):
        sent = msg.role == MessageRole.USER

        if msg.role == MessageRole.THOUGHT:
            # We still support this for live streaming, but history should prefer inline thoughts
            with ui.row().classes("w-full justify-start"):
                with ui.card().classes(
                    "bg-yellow-900/20 border border-yellow-700/50 p-2 w-full max-w-3xl"
                ):
                    ui.label("💭 Thinking...").classes(
                        "text-xs text-yellow-500 font-bold mb-1"
                    )
                    thought_text = msg.thought or ""
                    ui.markdown(thought_text).classes("text-sm text-yellow-200 italic chat-markdown")
            return

        if msg.role == MessageRole.TOOL:
            # Render tool results in history
            tool_name = msg.name or "Tool Result"
            self.add_tool_result(tool_name, msg.content, is_error=False)
            return

        if msg.role == MessageRole.SYSTEM:
            if msg.content:
                self.add_system_message(msg.content)
            return

        # Custom Chat Bubble Implementation
        row_classes = "w-full justify-end" if sent else "w-full justify-start"

        with ui.row().classes(row_classes + " gap-2 group"):
            # Avatar area
            if not sent:
                ui.label(name).classes("text-xs font-bold text-gray-400 mt-1 self-start")

            with ui.column().classes("max-w-[80%] items-end" if sent else "max-w-[80%] items-start"):
                # Using a DIV as the bubble
                bubble = ui.element('div').classes("p-3 rounded-2xl relative shadow-sm")

                # Apply styles via classes
                if sent:
                    # User: Green
                    bubble.classes(Theme.chat_bubble_sent + " rounded-tr-none")
                else:
                    # AI: Dark Grey
                    bubble.classes(Theme.chat_bubble_received + " rounded-tl-none")

                with bubble:
                    # Context Menu attached to the bubble
                    content_container = ui.column().classes("w-full p-0 m-0 gap-1")
                    with ui.context_menu():
                        # Use a local variable to capture content_container for the lambda
                        current_container = content_container
                        ui.menu_item("Edit", on_click=lambda: self._toggle_edit_mode(current_container, index, msg))
                        ui.menu_item("Delete", on_click=lambda: self._delete_message(index)).classes("text-red-400")
                        if not sent:
                            ui.separator()
                            ui.menu_item("Regenerate from here", on_click=lambda: self._regenerate_from(index))

                    with content_container:
                        # 1. Thinking (if present in Assistant message)
                        if msg.thought:
                             with ui.card().classes(
                                "bg-yellow-900/10 border-l-2 border-yellow-700/50 p-2 mb-2 w-full shadow-none"
                            ):
                                ui.label("💭 Thought Process").classes("text-[10px] text-yellow-600 font-bold uppercase")
                                ui.markdown(msg.thought).classes("text-xs text-yellow-200/70 italic chat-markdown")

                        # 2. Narrative Content
                        msg_content = msg.content or ""
                        if msg_content:
                            ui.markdown(msg_content).classes(
                                "w-full min-w-0 break-words break-all chat-markdown prose prose-invert max-w-none text-sm [&_*]:text-inherit"
                            )

                        # 3. Tool Calls (if present)
                        if msg.tool_calls:
                            for tc in msg.tool_calls:
                                with ui.expansion(f"🛠 {tc.get('name')}", icon="settings").classes(
                                    "w-full bg-slate-800/50 border border-slate-700/50 rounded-lg text-[10px] mt-2"
                                ):
                                    ui.code(json.dumps(tc.get("arguments"), indent=2)).classes("text-[10px] text-gray-500")

                    # Edit Button (visible on hover)
                    with ui.row().classes(
                        "opacity-0 group-hover:opacity-100 transition-opacity absolute -right-2 -top-2 bg-slate-900 rounded-full shadow-sm z-10"
                    ):
                        ui.button(
                            icon="edit",
                            on_click=lambda: self._toggle_edit_mode(content_container, index, msg),
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
        if not session:
            return

        if 0 <= index < len(session.history):
            session.history[index].content = new_content
            game_session = self.session_manager.get_active_session()
            if game_session:
                game_session.session_data = session.to_json()
                if self.session_manager.db and self.session_manager.db.sessions:
                    self.session_manager.db.sessions.update(game_session)
                    ui.notify("Message updated")
            self.load_history()


    def _delete_message(self, index):
        session = self.orchestrator.session
        if not session:
            return

        if 0 <= index < len(session.history):
            session.history.pop(index)
            game_session = self.session_manager.get_active_session()
            if game_session:
                game_session.session_data = session.to_json()
                if self.session_manager.db and self.session_manager.db.sessions:
                    self.session_manager.db.sessions.update(game_session)
                    ui.notify("Message deleted")
            self.load_history()


    def _regenerate_from(self, index):
        if not self.orchestrator.session:
            return

        game_session = self.session_manager.get_active_session()
        if game_session:
            self.set_generating(True)
            self.orchestrator.regenerate_from_index(game_session, index)


    def add_message(self, name: str, text: str, role: str, index: int | None = None, message_data: dict | None = None):
        if not self.container:
            return

        # Sync history if message_data is provided (ensures index is valid for interactive rendering)
        if message_data and self.orchestrator.session:
            history = self.orchestrator.session.history
            # Ensure the history has enough entries up to the index
            if index is not None:
                while len(history) <= index:
                    # Append a placeholder or the actual message if it's the target index
                    if len(history) == index:
                        history.append(Message(**message_data))
                    else:
                        # This shouldn't happen often, but fill gaps if they occur
                        history.append(Message(role="system", content=""))

        # If we have an index and it's a standard message role, use the interactive renderer
        if index is not None and role in [MessageRole.USER, MessageRole.ASSISTANT]:
            session = self.orchestrator.session
            if session and 0 <= index < len(session.history):
                msg = session.history[index]
                with self.container:
                    self._render_interactive_message(index, msg, name)
                self._scroll_down()
                return

        with self.container:
            sent = role == MessageRole.USER
            if role == MessageRole.THOUGHT:
                with ui.row().classes("w-full justify-start"):
                    with ui.card().classes(
                        "bg-yellow-900/20 border border-yellow-700/50 p-2 w-full max-w-3xl"
                    ):
                        ui.label("💭 Thinking...").classes(
                            "text-xs text-yellow-500 font-bold mb-1"
                        )
                        ui.markdown(text or "").classes("text-sm text-yellow-200 italic chat-markdown")
            else:
                # Fallback for system messages or messages without valid history index
                row_classes = "w-full justify-end" if sent else "w-full justify-start"

                with ui.row().classes(row_classes + " gap-2"):
                    if not sent:
                        ui.label(name).classes("text-xs font-bold text-gray-400 mt-1 self-start")

                    with ui.column().classes("max-w-[80%] items-end" if sent else "max-w-[80%] items-start"):
                        bubble = ui.element('div').classes("p-3 rounded-2xl shadow-sm")

                        # Apply Theme classes (same as history rendering)
                        if sent:
                            bubble.classes(Theme.chat_bubble_sent + " rounded-tr-none")
                        else:
                            bubble.classes(Theme.chat_bubble_received + " rounded-tl-none")

                        with bubble:
                            ui.markdown(text or "").classes(
                                "w-full min-w-0 break-words break-all chat-markdown prose prose-invert max-w-none text-sm [&_*]:text-inherit"
                            )
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

    def add_tool_result(self, name: str, content: Any, is_error: bool = False):
        if not self.container:
            return

        if isinstance(content, dict):
            display_content = json.dumps(content, indent=2)
        else:
            display_content = str(content)

        label = f"🛠 {name}"
        if is_error:
            label = f"⚠️ {name} (Error)"

        with self.container:
            with ui.row().classes("w-full justify-start"):
                with ui.expansion(label, icon="code").classes(
                    "w-full max-w-lg bg-slate-900/60 border border-slate-800 rounded text-xs opacity-80"
                ):
                    ui.code(display_content).classes("text-xs text-gray-400 overflow-x-auto")
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

    def add_rag_context(self, text: str, memory_ids: list):
        if not self.container or not text:
            return

        # Count memories by counting lines starting with emojis or symbols
        # (Assuming the format from MemoryRetriever.format_for_prompt)
        m_count = len([line for line in text.split('\n') if line.strip() and not line.startswith('#')])

        with self.container:
            with ui.row().classes("w-full justify-start"):
                with ui.expansion(
                    f"🧠 Recalled {m_count} context items...",
                    icon="psychology"
                ).classes(
                    "w-full max-w-lg bg-slate-900/40 border border-blue-900/30 rounded-lg text-xs"
                ) as exp:
                    exp.classes("text-blue-400 font-medium")
                    with ui.column().classes("p-2 gap-1"):
                        ui.markdown(text).classes("text-xs text-gray-400 chat-markdown prose prose-invert max-w-none")
                        if memory_ids:
                             ui.label(f"IDs: {memory_ids}").classes("text-[10px] text-gray-600 font-mono mt-1")

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
        if self.input_area:
            self.input_area.value = text
            self.handle_enter()


    def handle_enter(self):
        if not self.input_area:
            return
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
