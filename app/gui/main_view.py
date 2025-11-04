import tkinter
import customtkinter as ctk
from datetime import datetime
from typing import List
from app.gui.collapsible_frame import CollapsibleFrame
from app.gui.world_info_manager_view import WorldInfoManagerView
from app.gui.styles import (
    ACTIVE_THEME as Theme,
    get_chat_bubble_style,
    get_tool_call_style,
    get_button_style,
)
import queue # Added for UI queue
import logging # Added for logging
from app.gui.state_inspector_views import CharacterInspectorView, InventoryInspectorView, QuestInspectorView

logger = logging.getLogger(__name__)

class MainView(ctk.CTk):
    def __init__(self, db_manager):
        super().__init__()

        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self.selected_prompt = None
        self.selected_session = None
        self.title("AI-RPG")
        self.geometry(f"{Theme.dimensions.window_width}x{Theme.dimensions.window_height}")

        # Track bubble content labels for resize updates
        self.bubble_labels: List[ctk.CTkLabel] = []
        self._last_chat_width = 0  # Track width changes

        # Main layout
        self.grid_columnconfigure(0, weight=6)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main Panel
        self.main_panel = ctk.CTkFrame(self, fg_color=Theme.colors.bg_primary)
        self.main_panel.grid(row=0, column=0, sticky="nsew", padx=Theme.spacing.padding_md, pady=Theme.spacing.padding_md)
        self.main_panel.grid_rowconfigure(1, weight=1) # chat takes the space
        self.main_panel.grid_columnconfigure(0, weight=1)

        # Game time header bar
        self.game_time_frame = ctk.CTkFrame(self.main_panel, fg_color=Theme.colors.bg_tertiary, height=40)
        self.game_time_frame.grid(row=0, column=0, columnspan=2, sticky="ew", 
                                  padx=Theme.spacing.padding_sm, pady=(Theme.spacing.padding_sm, 0))
        self.game_time_frame.grid_propagate(False)

        self.game_time_label = ctk.CTkLabel(
            self.game_time_frame,
            text="🕐 Day 1, Dawn",
            font=Theme.fonts.subheading,
            text_color=Theme.colors.text_gold
        )
        self.game_time_label.pack(side="left", padx=Theme.spacing.padding_md, pady=Theme.spacing.padding_sm)

        # Session name label (bonus feature)
        self.session_name_label = ctk.CTkLabel(
            self.game_time_frame,
            text="No session loaded",
            font=Theme.fonts.body_small,
            text_color=Theme.colors.text_muted
        )
        self.session_name_label.pack(side="right", padx=Theme.spacing.padding_md, pady=Theme.spacing.padding_sm)

        # Chat history - scrollable frame
        self.chat_history_frame = ctk.CTkScrollableFrame(self.main_panel, fg_color=Theme.colors.bg_secondary)
        self.chat_history_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", 
                                     padx=Theme.spacing.padding_sm, pady=Theme.spacing.padding_sm)

        # Bind to main window resize instead of the scrollable frame
        self.bind("<Configure>", self._on_window_resize)

        # Choice buttons frame
        self.choice_button_frame = ctk.CTkFrame(self.main_panel)
        self.choice_button_frame.grid(row=2, column=0, columnspan=2, sticky="ew", 
                                      padx=Theme.spacing.padding_sm, pady=Theme.spacing.padding_sm)
        self.choice_button_frame.grid_remove()

        self.user_input = ctk.CTkTextbox(self.main_panel, height=Theme.spacing.input_height)
        self.user_input.grid(row=3, column=0, sticky="ew", 
                            padx=Theme.spacing.padding_sm, pady=Theme.spacing.padding_sm)

        button_frame = ctk.CTkFrame(self.main_panel)
        button_frame.grid(row=3, column=1, sticky="ns", 
                         padx=Theme.spacing.padding_sm, pady=Theme.spacing.padding_sm)

        self.send_button = ctk.CTkButton(button_frame, text="Send", state="disabled", command=self.handle_send_button)
        self.send_button.pack(expand=True, fill="both", padx=Theme.spacing.padding_xs, pady=Theme.spacing.padding_xs)

        self.stop_button = ctk.CTkButton(button_frame, text="Stop")
        self.stop_button.pack(expand=True, fill="both", padx=Theme.spacing.padding_xs, pady=Theme.spacing.padding_xs)

        # Loading indicator
        self.loading_frame = ctk.CTkFrame(self.main_panel, fg_color=Theme.colors.bg_tertiary)
        self.loading_label = ctk.CTkLabel(
            self.loading_frame,
            text="🤔 AI is thinking...",
            font=Theme.fonts.subheading,
            text_color=Theme.colors.text_gold
        )
        self.loading_label.pack(pady=10)
        # Don't grid frame yet - show/hide on demand
        # self.loading_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=Theme.spacing.padding_sm, pady=Theme.spacing.padding_sm)
        # It will be gridded dynamically in _handle_ui_message

        # Control Panel (scrollable)
        self.control_panel = ctk.CTkScrollableFrame(self, fg_color=Theme.colors.bg_primary)
        self.control_panel.grid(row=0, column=1, sticky="nsew", 
                               padx=(0, Theme.spacing.padding_md), pady=Theme.spacing.padding_md)
        
        self.prompt_collapsible = None
        self.session_collapsible = None
        
        self._create_right_panel_widgets()

        self.refresh_prompt_list()
        self.refresh_session_list()
        self.after(100, self._process_ui_queue) # Start UI queue polling

    def _calculate_bubble_width(self) -> int:
        """Calculate the appropriate bubble width based on chat frame width."""
        # Get the actual width of the chat frame
        # We need to account for scrollbar and padding
        frame_width = self.chat_history_frame.winfo_width()
        
        # If window hasn't been drawn yet, use a default
        if frame_width <= 1:
            frame_width = Theme.dimensions.window_width * 0.75  # Estimate based on window width
        
        # Subtract scrollbar width (approximately 15-20 pixels) and padding
        usable_width = frame_width - 30
        
        # Calculate percentage-based width
        bubble_width = int(usable_width * Theme.spacing.bubble_width_percent)
        
        # Ensure minimum width
        bubble_width = max(bubble_width, Theme.spacing.bubble_min_width)
        
        return bubble_width

    def _on_window_resize(self, event):
        """Update all bubble widths when the window is resized."""
        # Only update if the window width actually changed significantly
        current_width = self.winfo_width()
        
        if abs(current_width - self._last_chat_width) > 50:  # Only update if changed by 50+ pixels
            self._last_chat_width = current_width
            new_width = self._calculate_bubble_width()
            
            # ✅ FIX: Clean up destroyed widgets while updating
            active_labels = []
            for label in self.bubble_labels:
                try:
                    if label.winfo_exists():
                        label.configure(wraplength=new_width)
                        active_labels.append(label)  # Keep only active widgets
                    # If winfo_exists() is False, widget is destroyed - don't add to list
                except (tkinter.TclError, AttributeError, RuntimeError):
                    # Widget is destroyed or invalid - skip it
                    pass
            
            # ✅ FIX: Replace list with only active widgets
            self.bubble_labels = active_labels

    def _scroll_to_bottom(self):
        """Scroll the chat to the bottom."""
        # Use after_idle to ensure the frame is updated before scrolling
        self.after_idle(lambda: self.chat_history_frame._parent_canvas.yview_moveto(1.0))

    def _process_ui_queue(self):
        """Process messages from the orchestrator's UI queue."""
        try:
            processed = 0
            while True:  # Process all pending messages
                msg = self.orchestrator.ui_queue.get_nowait()
                self._handle_ui_message(msg)
                processed += 1
        except queue.Empty:
            pass
        finally:
            if processed > 0:
                self.logger.debug(f"📬 Processed {processed} UI messages")  # âœ… Add this
            # Re-schedule polling
            self.after(100, self._process_ui_queue)

    def _handle_ui_message(self, msg: dict):
        """Handle a single UI message from the orchestrator."""
        msg_type = msg.get("type")

        self.logger.debug(f"📨 UI message received: {msg_type}") 

        if msg_type == "thought_bubble":
            # Show loading frame using grid
            self.loading_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=Theme.spacing.padding_sm, pady=Theme.spacing.padding_sm)
            self.add_message_bubble("thought", msg["content"])
        
        elif msg_type == "message_bubble":
            self.add_message_bubble(msg["role"], msg["content"])
        
        elif msg_type == "tool_call":
            self.logger.debug(f"🔧 Adding tool call to panel: {msg.get('name')}")
            self.add_tool_call(msg["name"], msg["args"])
        
        elif msg_type == "tool_result":
            self.add_tool_result(msg["result"], msg.get("is_error", False))
        
        elif msg_type == "narrative": # This type is now handled by message_bubble with role "assistant"
            self.add_message_bubble("assistant", msg["content"])
        
        elif msg_type == "choices":
            self.display_action_choices(msg["choices"])
        
        elif msg_type == "error":
            self.add_message_bubble("system", f"❌ Error: {msg['message']}")
        
        elif msg_type == "turn_complete":
            self.loading_frame.grid_remove() # Hide loading
            self.send_button.configure(state="normal") # Re-enable
            # Refresh inspectors if needed
            if hasattr(self, 'character_inspector'):
                self.character_inspector.refresh()
            if hasattr(self, 'inventory_inspector'):
                self.inventory_inspector.refresh()
            if hasattr(self, 'quest_inspector'):
                self.quest_inspector.refresh()
        
        elif msg_type == "refresh_memory_inspector":
            if hasattr(self, 'memory_inspector'):
                self.memory_inspector.refresh_memories()
        
        elif msg_type == "update_game_time":
            self.game_time_label.configure(text=f"🕐 {msg['new_time']}")

        elif msg_type == "tool_event":
            # This is for the legacy tool_event_callback, now routed through queue
            logger.info(f"Tool Event: {msg['message']}")
            # Optionally display this in a specific debug area or log
        
        else:
            logger.warning(f"Unknown UI message type: {msg_type}")

    def add_message_bubble(self, role: str, content: str):
        """Add a message as a chat bubble."""
        style = get_chat_bubble_style(role)
        
        bubble_container = ctk.CTkFrame(self.chat_history_frame, fg_color="transparent")
        bubble_container.pack(fill="x", padx=Theme.spacing.padding_md, pady=Theme.spacing.bubble_margin)
        
        bubble_kwargs = {
            "fg_color": style["fg_color"],
            "corner_radius": style["corner_radius"]
        }
        if "border_width" in style:
            bubble_kwargs["border_width"] = style["border_width"]
            bubble_kwargs["border_color"] = style["border_color"]
        
        bubble = ctk.CTkFrame(bubble_container, **bubble_kwargs)
        bubble.pack(anchor=style["anchor"], padx=Theme.spacing.padding_sm)
        
        role_label = ctk.CTkLabel(
            bubble,
            text=style["label"],
            font=Theme.fonts.body_small if role != "thought" else Theme.fonts.body_italic,
            text_color=style["text_color"]
        )
        role_label.pack(anchor="w", padx=Theme.spacing.bubble_padding_x, 
                       pady=(Theme.spacing.bubble_padding_y_top, 0))
        
        # Calculate dynamic width
        bubble_width = self._calculate_bubble_width()
        
        content_label = ctk.CTkLabel(
            bubble,
            text=content,
            font=Theme.fonts.body if role != "thought" else Theme.fonts.body_italic,
            text_color=style["text_color"],
            wraplength=bubble_width,
            justify="left"
        )
        content_label.pack(anchor="w", padx=Theme.spacing.padding_md, 
                          pady=(Theme.spacing.padding_xs, Theme.spacing.bubble_padding_y_bottom))
        
        # Store reference to the label for resize updates
        self.bubble_labels.append(content_label)
        
        # Auto-scroll to bottom (use our helper method)
        self._scroll_to_bottom()

    def clear_chat_history(self):
        """Clear all chat bubbles."""
        for widget in self.chat_history_frame.winfo_children():
            widget.destroy()
        # ✅ FIX: Clear the bubble_labels list immediately
        self.bubble_labels.clear()

    def _create_right_panel_widgets(self):
        pack_config = {
            "pady": Theme.spacing.padding_sm,
            "padx": Theme.spacing.padding_sm,
            "fill": "x",
            "expand": False
        }
        
        # ==================== Prompt Management ====================
        self.prompt_collapsible = CollapsibleFrame(self.control_panel, "Prompt Management")
        self.prompt_collapsible.pack(**pack_config)
        
        prompt_content = self.prompt_collapsible.get_content_frame()
        
        self.prompt_scrollable_frame = ctk.CTkScrollableFrame(
            prompt_content, 
            height=Theme.spacing.scrollable_frame_height
        )
        self.prompt_scrollable_frame.pack(**pack_config)

        prompt_button_frame = ctk.CTkFrame(prompt_content)
        prompt_button_frame.pack(**pack_config)

        new_prompt_button = ctk.CTkButton(
            prompt_button_frame, text="New", command=self.new_prompt, 
            width=Theme.dimensions.button_small
        )
        new_prompt_button.pack(side="left", padx=Theme.spacing.padding_xs)

        edit_prompt_button = ctk.CTkButton(
            prompt_button_frame, text="Edit", command=self.edit_prompt, 
            width=Theme.dimensions.button_small
        )
        edit_prompt_button.pack(side="left", padx=Theme.spacing.padding_xs)

        delete_prompt_button = ctk.CTkButton(
            prompt_button_frame, text="Delete", command=self.delete_prompt, 
            width=Theme.dimensions.button_small
        )
        delete_prompt_button.pack(side="left", padx=Theme.spacing.padding_xs)

        # ==================== Game Sessions ====================
        self.session_collapsible = CollapsibleFrame(self.control_panel, "Game Sessions")
        self.session_collapsible.pack(**pack_config)
        
        session_content = self.session_collapsible.get_content_frame()
        
        self.session_scrollable_frame = ctk.CTkScrollableFrame(
            session_content, 
            height=Theme.spacing.scrollable_frame_height
        )
        self.session_scrollable_frame.pack(**pack_config)

        new_game_button = ctk.CTkButton(session_content, text="New Game", command=self.new_game)
        new_game_button.pack(**pack_config)

        # ==================== Advanced Context ====================
        context_collapsible = CollapsibleFrame(self.control_panel, "Advanced Context")
        context_collapsible.pack(**pack_config)
        
        context_content = context_collapsible.get_content_frame()

        memory_label = ctk.CTkLabel(context_content, text="Memory:")
        memory_label.pack(pady=(Theme.spacing.padding_sm, 0), padx=Theme.spacing.padding_sm, anchor="w")
        
        self.memory_textbox = ctk.CTkTextbox(context_content, height=Theme.spacing.textbox_small)
        self.memory_textbox.pack(**pack_config)

        authors_note_label = ctk.CTkLabel(context_content, text="Author's Note:")
        authors_note_label.pack(pady=(Theme.spacing.padding_sm, 0), padx=Theme.spacing.padding_sm, anchor="w")
        
        self.authors_note_textbox = ctk.CTkTextbox(context_content, height=Theme.spacing.textbox_small)
        self.authors_note_textbox.pack(**pack_config)

        world_info_button = ctk.CTkButton(context_content, text="Manage World Info", command=self.open_world_info_manager)
        world_info_button.pack(**pack_config)

        save_context_button = ctk.CTkButton(context_content, text="Save Context", command=self.save_context)
        save_context_button.pack(**pack_config)


        # ==================== Game State Inspector ====================
        inspector_collapsible = CollapsibleFrame(self.control_panel, "Game State Inspector")
        inspector_collapsible.pack(pady=Theme.spacing.padding_sm, padx=Theme.spacing.padding_sm, 
                                  fill="both", expand=True)
        
        inspector_content = inspector_collapsible.get_content_frame()

        self.game_state_inspector_tabs = ctk.CTkTabview(inspector_content)
        self.game_state_inspector_tabs.pack(fill="both", expand=True)
        self.game_state_inspector_tabs.add("Characters")
        self.game_state_inspector_tabs.add("Inventory")
        self.game_state_inspector_tabs.add("Quests")
        self.game_state_inspector_tabs.add("Memories")
        self.game_state_inspector_tabs.add("Tool Calls")
        self.game_state_inspector_tabs.add("State Viewer") # Add new tab

        # Add the actual views:
        self.character_inspector = CharacterInspectorView(
            self.game_state_inspector_tabs.tab("Characters"),
            self.db_manager # Pass db_manager directly
        )
        self.character_inspector.pack(fill="both", expand=True)

        self.inventory_inspector = InventoryInspectorView(
            self.game_state_inspector_tabs.tab("Inventory"),
            self.db_manager # Pass db_manager directly
        )
        self.inventory_inspector.pack(fill="both", expand=True)

        self.quest_inspector = QuestInspectorView(
            self.game_state_inspector_tabs.tab("Quests"),
            self.db_manager # Pass db_manager directly
        )
        self.quest_inspector.pack(fill="both", expand=True)

        from app.gui.memory_inspector_view import MemoryInspectorView
        self.memory_inspector = MemoryInspectorView(
            self.game_state_inspector_tabs.tab("Memories"),
            self.db_manager,
            None
        )
        self.memory_inspector.pack(fill="both", expand=True)

        self.tool_calls_frame = ctk.CTkScrollableFrame(
            self.game_state_inspector_tabs.tab("Tool Calls"),
            fg_color=Theme.colors.bg_secondary
        )
        self.tool_calls_frame.pack(fill="both", expand=True)

        # Add button to open the viewer
        state_viewer_frame = self.game_state_inspector_tabs.tab("State Viewer")
        ctk.CTkButton(
            state_viewer_frame,
            text="🔍 Open State Viewer",
            command=self.open_state_viewer,
            height=50
        ).pack(expand=True)

    def add_tool_call(self, tool_name: str, args: dict):
        """Add a tool call to the dedicated tool calls panel."""
        self.logger.debug(f"🛠️ add_tool_call called: {tool_name}")
        self.logger.debug(f"   tool_calls_frame exists: {hasattr(self, 'tool_calls_frame')}")
        style = get_tool_call_style()
        
        call_frame = ctk.CTkFrame(
            self.tool_calls_frame, 
            fg_color=style["fg_color"], 
            corner_radius=style["corner_radius"]
        )
        call_frame.pack(fill="x", padx=style["padding"], pady=style["margin"])
        
        header = ctk.CTkLabel(
            call_frame,
            text=f"🛠 {tool_name}",
            font=Theme.fonts.subheading,
            text_color=style["header_color"]
        )
        header.pack(anchor="w", padx=Theme.spacing.padding_md, pady=(Theme.spacing.padding_sm, Theme.spacing.padding_xs))
        
        args_text = str(args)
        if len(args_text) > 100:
            args_text = args_text[:100] + "..."
        
        args_label = ctk.CTkLabel(
            call_frame,
            text=f"Args: {args_text}",
            font=Theme.fonts.monospace,
            text_color=style["text_color"],
            wraplength=Theme.dimensions.wrap_tool,
            justify="left"
        )
        args_label.pack(anchor="w", padx=Theme.spacing.padding_md, pady=(0, Theme.spacing.padding_sm))
        
        # Auto-scroll tool calls panel
        self.after_idle(lambda: self.tool_calls_frame._parent_canvas.yview_moveto(1.0))

    def add_tool_result(self, result: any, is_error: bool = False):
        """Add a tool result to the dedicated tool calls panel."""
        children = self.tool_calls_frame.winfo_children()
        if not children:
            return
        
        last_frame = children[-1]
        style = get_tool_call_style()
        
        result_text = str(result)
        if len(result_text) > 200:
            result_text = result_text[:200] + "..."
        
        color = style["error_color"] if is_error else style["success_color"]
        icon = "❌" if is_error else "✓"
        
        result_label = ctk.CTkLabel(
            last_frame,
            text=f"{icon} Result: {result_text}",
            font=Theme.fonts.monospace,
            text_color=color,
            wraplength=Theme.dimensions.wrap_tool,
            justify="left"
        )
        result_label.pack(anchor="w", padx=Theme.spacing.padding_md, pady=(0, Theme.spacing.padding_sm))
        
        # Auto-scroll tool calls panel
        self.after_idle(lambda: self.tool_calls_frame._parent_canvas.yview_moveto(1.0))

    def log_tool_event(self, message: str):
        """Legacy method - now sends tool events to the UI queue."""
        if hasattr(self, 'orchestrator') and self.orchestrator:
            self.orchestrator.ui_queue.put({"type": "tool_event", "message": message})
        else:
            logger.warning(f"Orchestrator not set, cannot log tool event: {message}")

    def get_input(self) -> str:
        return self.user_input.get("1.0", "end-1c")

    def clear_input(self):
        self.user_input.delete("1.0", "end")

    def display_action_choices(self, choices: List[str]):
        """Display action choice buttons for the user to click."""
        for widget in self.choice_button_frame.winfo_children():
            widget.destroy()
        
        if not choices:
            self.choice_button_frame.grid_remove()
            return
        
        self.choice_button_frame.grid()
        
        for i, choice in enumerate(choices):
            btn = ctk.CTkButton(
                self.choice_button_frame,
                text=f"{i+1}. {choice}",
                command=lambda c=choice: self.select_choice(c)
            )
            btn.pack(side="left", padx=5, pady=5, expand=True, fill="x")

    def select_choice(self, choice: str):
        """Handle when a user clicks an action choice."""
        self.user_input.delete("1.0", "end")
        self.user_input.insert("1.0", choice)
        self.choice_button_frame.grid_remove()
        self.handle_send_button()

    def new_game(self):
        if not self.selected_prompt:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        session_name = f"{timestamp}_{self.selected_prompt.name}"

        self.orchestrator.new_session(self.selected_prompt.content)
        self.orchestrator.save_game(session_name, self.selected_prompt.id)
        self.refresh_session_list(self.selected_prompt.id)

    def handle_send_button(self):
        if not self.selected_session:
            return
        
        # Disable to prevent concurrent turns
        self.send_button.configure(state="disabled")
        
        # Clear previous choices
        for widget in self.choice_button_frame.winfo_children():
            widget.destroy()
        self.choice_button_frame.grid_remove()
        
        # Start turn (non-blocking)
        self.orchestrator.plan_and_execute(self.selected_session)

    def load_game(self, session_id: int):
        self.orchestrator.load_game(session_id)
        self.clear_chat_history()
        
        history = self.orchestrator.session.get_history()
        for message in history:
            if message.role == "user":
                self.add_message_bubble("user", message.content)
            elif message.role == "assistant":
                self.add_message_bubble("assistant", message.content)
            elif message.role == "system": # Also display system messages from history
                self.add_message_bubble("system", message.content)
        
        self.load_context()

    def load_context(self):
        """Load memory and author's note for the current session."""
        if not self.selected_session:
            return
        
        context = self.db_manager.get_session_context(self.selected_session.id)
        if context:
            self.memory_textbox.delete("1.0", "end")
            self.memory_textbox.insert("1.0", context.get("memory", ""))
            
            self.authors_note_textbox.delete("1.0", "end")
            self.authors_note_textbox.insert("1.0", context.get("authors_note", ""))

    def save_context(self):
        """Save the current memory and author's note."""
        if not self.selected_session:
            return
        
        memory = self.memory_textbox.get("1.0", "end-1c")
        authors_note = self.authors_note_textbox.get("1.0", "end-1c")
        
        self.db_manager.update_session_context(self.selected_session.id, memory, authors_note)
        self.add_message_bubble("system", "Context saved")

    def open_world_info_manager(self):
        if not self.selected_prompt:
            self.add_message_bubble("system", "Please select a prompt first")
            return

        # Pass vector store through orchestrator
        world_info_view = WorldInfoManagerView(self, self.db_manager, self.selected_prompt.id, getattr(self.orchestrator, "vector_store", None))
        world_info_view.grab_set()

    def refresh_session_list(self, prompt_id: int | None = None):
        for widget in self.session_scrollable_frame.winfo_children():
            widget.destroy()

        if prompt_id:
            sessions = self.db_manager.get_sessions_by_prompt(prompt_id)
            for session in sessions:
                btn = ctk.CTkButton(
                    self.session_scrollable_frame, 
                    text=session.name,
                    command=lambda s=session: self.on_session_select(s)
                )
                btn.pack(pady=2, padx=5, fill="x")

    def refresh_prompt_list(self):
        for widget in self.prompt_scrollable_frame.winfo_children():
            widget.destroy()
            
        prompts = self.db_manager.get_all_prompts()
        
        for prompt in prompts:
            btn = ctk.CTkButton(
                self.prompt_scrollable_frame, 
                text=prompt.name,
                command=lambda p=prompt: self.on_prompt_select(p)
            )
            btn.pack(pady=2, padx=5, fill="x")

    def on_prompt_select(self, prompt):
        self.selected_prompt = prompt
        self.selected_session = None
        self.send_button.configure(state="disabled")
        self.refresh_session_list(prompt.id)
        
        button_styles = get_button_style()
        selected_style = get_button_style("selected")
        
        for widget in self.prompt_scrollable_frame.winfo_children():
            if widget.cget("text") == prompt.name:
                widget.configure(fg_color=selected_style["fg_color"])
            else:
                widget.configure(fg_color=button_styles["fg_color"])
        
        if self.prompt_collapsible and not self.prompt_collapsible.is_collapsed:
            self.prompt_collapsible.toggle()

    def on_session_select(self, session):
        self.selected_session = session
        self.load_game(session.id)
        self.send_button.configure(state="normal")
        
        # ✅ Update header
        self.session_name_label.configure(text=session.name)
        self.game_time_label.configure(text=f"🕐 {session.game_time}")
        
        if hasattr(self, 'memory_inspector'):
            self.memory_inspector.set_session(session.id)
        
        # ✅ Refresh all inspectors
        if hasattr(self, 'character_inspector'):
            self.character_inspector.refresh()
        
        if hasattr(self, 'inventory_inspector'):
            self.inventory_inspector.refresh()
        
        if hasattr(self, 'quest_inspector'):
            self.quest_inspector.refresh()
        
        # ... rest of button styling code ...
        button_styles = get_button_style()
        selected_style = get_button_style("selected")
        
        for widget in self.session_scrollable_frame.winfo_children():
            if widget.cget("text") == session.name:
                widget.configure(fg_color=selected_style["fg_color"])
            else:
                widget.configure(fg_color=button_styles["fg_color"])
        
        if self.session_collapsible and not self.session_collapsible.is_collapsed:
            self.session_collapsible.toggle()

    def new_prompt(self):
        dialog = ctk.CTkInputDialog(text="Enter prompt name:", title="New Prompt")
        name = dialog.get_input()
        if name:
            content_dialog = ctk.CTkInputDialog(text="Enter prompt content:", title="New Prompt")
            content = content_dialog.get_input()
            if content:
                self.db_manager.create_prompt(name, content)
                self.refresh_prompt_list()

    def edit_prompt(self):
        if not self.selected_prompt:
            return
        
        name_dialog = ctk.CTkInputDialog(text="Enter new name:", title="Edit Prompt")
        name = name_dialog.get_input()
        if name:
            content_dialog = ctk.CTkInputDialog(text="Enter new content:", title="Edit Prompt")
            content = content_dialog.get_input()
            if content:
                self.selected_prompt.name = name
                self.selected_prompt.content = content
                self.db_manager.update_prompt(self.selected_prompt)
                self.refresh_prompt_list()

    def delete_prompt(self):
        if not self.selected_prompt:
            return
        
        self.db_manager.delete_prompt(self.selected_prompt.id)
        self.selected_prompt = None
        self.refresh_prompt_list()

    def set_orchestrator(self, orchestrator):
        """Called from main.py after orchestrator is created."""
        self.orchestrator = orchestrator
        
        # Connect orchestrator to all inspectors
        if hasattr(self, 'character_inspector'):
            self.character_inspector.orchestrator = orchestrator
        
        if hasattr(self, 'inventory_inspector'):
            self.inventory_inspector.orchestrator = orchestrator
        
        if hasattr(self, 'quest_inspector'):
            self.quest_inspector.orchestrator = orchestrator
        
        if hasattr(self, 'memory_inspector'):
            self.memory_inspector.orchestrator = orchestrator

    def open_state_viewer(self):
        if not self.selected_session:
            return
        
        from app.gui.state_viewer_dialog import StateViewerDialog
        viewer = StateViewerDialog(self, self.db_manager, self.selected_session.id)
        viewer.grab_set()
