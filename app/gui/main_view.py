import customtkinter as ctk
from datetime import datetime
from typing import List
from app.gui.collapsible_frame import CollapsibleFrame
from app.gui.world_info_manager_view import WorldInfoManagerView

class MainView(ctk.CTk):
    def __init__(self, db_manager):
        super().__init__()

        self.db_manager = db_manager
        self.selected_prompt = None
        self.selected_session = None
        self.title("AI-RPG")
        self.geometry("1200x800")

        # Main layout
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main Panel
        self.main_panel = ctk.CTkFrame(self, fg_color="#2B2B2B")
        self.main_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_panel.grid_rowconfigure(0, weight=1)
        self.main_panel.grid_columnconfigure(0, weight=1)

        self.chat_history = ctk.CTkTextbox(self.main_panel, state="disabled")
        self.chat_history.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

        # Choice buttons frame
        self.choice_button_frame = ctk.CTkFrame(self.main_panel)
        self.choice_button_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.choice_button_frame.grid_remove()  # Hidden by default

        self.user_input = ctk.CTkTextbox(self.main_panel, height=100)
        self.user_input.grid(row=2, column=0, sticky="ew", padx=5, pady=5)

        button_frame = ctk.CTkFrame(self.main_panel)
        button_frame.grid(row=2, column=1, sticky="ns", padx=5, pady=5)

        self.send_button = ctk.CTkButton(button_frame, text="Send", state="disabled", command=self.handle_send_button)
        self.send_button.pack(expand=True, fill="both", padx=2, pady=2)

        self.stop_button = ctk.CTkButton(button_frame, text="Stop")
        self.stop_button.pack(expand=True, fill="both", padx=2, pady=2)

        # Control Panel (scrollable)
        self.control_panel = ctk.CTkScrollableFrame(self, fg_color="#2B2B2B")
        self.control_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        
        # Store references to collapsible frames for auto-collapse
        self.prompt_collapsible = None
        self.session_collapsible = None
        
        self._create_right_panel_widgets()

        self.refresh_prompt_list()
        self.refresh_session_list()

    def _create_right_panel_widgets(self):
        # ==================== Prompt Management (FIRST) ====================
        self.prompt_collapsible = CollapsibleFrame(self.control_panel, "Prompt Management")
        self.prompt_collapsible.pack(pady=5, padx=5, fill="x", expand=False)
        
        prompt_content = self.prompt_collapsible.get_content_frame()
        
        self.prompt_scrollable_frame = ctk.CTkScrollableFrame(prompt_content, height=100)
        self.prompt_scrollable_frame.pack(pady=5, padx=5, fill="x")

        # Prompt CRUD buttons
        prompt_button_frame = ctk.CTkFrame(prompt_content)
        prompt_button_frame.pack(pady=5, padx=5, fill="x")

        new_prompt_button = ctk.CTkButton(prompt_button_frame, text="New", command=self.new_prompt, width=60)
        new_prompt_button.pack(side="left", padx=2)

        edit_prompt_button = ctk.CTkButton(prompt_button_frame, text="Edit", command=self.edit_prompt, width=60)
        edit_prompt_button.pack(side="left", padx=2)

        delete_prompt_button = ctk.CTkButton(prompt_button_frame, text="Delete", command=self.delete_prompt, width=60)
        delete_prompt_button.pack(side="left", padx=2)

        # ==================== Game Sessions (SECOND) ====================
        self.session_collapsible = CollapsibleFrame(self.control_panel, "Game Sessions")
        self.session_collapsible.pack(pady=5, padx=5, fill="x", expand=False)
        
        session_content = self.session_collapsible.get_content_frame()
        
        self.session_scrollable_frame = ctk.CTkScrollableFrame(session_content, height=100)
        self.session_scrollable_frame.pack(pady=5, padx=5, fill="x")

        new_game_button = ctk.CTkButton(session_content, text="New Game", command=self.new_game)
        new_game_button.pack(pady=5, padx=5, fill="x")

        # ==================== Advanced Context ====================
        context_collapsible = CollapsibleFrame(self.control_panel, "Advanced Context")
        context_collapsible.pack(pady=5, padx=5, fill="x", expand=False)
        
        context_content = context_collapsible.get_content_frame()

        # Memory
        memory_label = ctk.CTkLabel(context_content, text="Memory:")
        memory_label.pack(pady=(5, 0), padx=5, anchor="w")
        
        self.memory_textbox = ctk.CTkTextbox(context_content, height=80)
        self.memory_textbox.pack(pady=5, padx=5, fill="x")

        # Author's Note
        authors_note_label = ctk.CTkLabel(context_content, text="Author's Note:")
        authors_note_label.pack(pady=(5, 0), padx=5, anchor="w")
        
        self.authors_note_textbox = ctk.CTkTextbox(context_content, height=80)
        self.authors_note_textbox.pack(pady=5, padx=5, fill="x")

        # World Info button
        world_info_button = ctk.CTkButton(context_content, text="Manage World Info", command=self.open_world_info_manager)
        world_info_button.pack(pady=5, padx=5, fill="x")

        # Save context button
        save_context_button = ctk.CTkButton(context_content, text="Save Context", command=self.save_context)
        save_context_button.pack(pady=5, padx=5, fill="x")

        # ==================== LLM Parameters ====================
        llm_collapsible = CollapsibleFrame(self.control_panel, "LLM Parameters")
        llm_collapsible.pack(pady=5, padx=5, fill="x", expand=False)
        
        llm_content = llm_collapsible.get_content_frame()

        provider_label = ctk.CTkLabel(llm_content, text="Provider:")
        provider_label.pack(pady=(5, 0), padx=5, anchor="w")

        self.provider_selector = ctk.CTkOptionMenu(llm_content, values=["Gemini", "OpenAI"])
        self.provider_selector.pack(pady=5, padx=5, fill="x")

        temp_label = ctk.CTkLabel(llm_content, text="Temperature:")
        temp_label.pack(pady=(5, 0), padx=5, anchor="w")

        self.temperature_slider = ctk.CTkSlider(llm_content)
        self.temperature_slider.pack(pady=5, padx=5, fill="x")

        top_p_label = ctk.CTkLabel(llm_content, text="Top P:")
        top_p_label.pack(pady=(5, 0), padx=5, anchor="w")

        self.top_p_slider = ctk.CTkSlider(llm_content)
        self.top_p_slider.pack(pady=5, padx=5, fill="x")

        # ==================== Game State Inspector ====================
        inspector_collapsible = CollapsibleFrame(self.control_panel, "Game State Inspector")
        inspector_collapsible.pack(pady=5, padx=5, fill="both", expand=True)
        
        inspector_content = inspector_collapsible.get_content_frame()

        self.game_state_inspector_tabs = ctk.CTkTabview(inspector_content)
        self.game_state_inspector_tabs.pack(fill="both", expand=True)
        self.game_state_inspector_tabs.add("Characters")
        self.game_state_inspector_tabs.add("Inventory")
        self.game_state_inspector_tabs.add("Quests")
        self.game_state_inspector_tabs.add("Memories")
        self.game_state_inspector_tabs.add("Tool Events")

        # Add memory inspector view
        from app.gui.memory_inspector_view import MemoryInspectorView
        self.memory_inspector = MemoryInspectorView(
            self.game_state_inspector_tabs.tab("Memories"),
            self.db_manager,
            None  # orchestrator will be set later
        )
        self.memory_inspector.pack(fill="both", expand=True)

        # Add a textbox for tool events
        self.tool_events_textbox = ctk.CTkTextbox(
            self.game_state_inspector_tabs.tab("Tool Events"), 
            state="disabled"
        )
        self.tool_events_textbox.pack(fill="both", expand=True)

    def log_tool_event(self, message: str):
        self.tool_events_textbox.configure(state="normal")
        self.tool_events_textbox.insert("end", message + "\n")
        self.tool_events_textbox.configure(state="disabled")
        self.tool_events_textbox.see("end")

    def add_message(self, message: str):
        self.chat_history.configure(state="normal")
        self.chat_history.insert("end", message)
        self.chat_history.configure(state="disabled")
        self.chat_history.see("end")

    def get_input(self) -> str:
        return self.user_input.get("1.0", "end-1c")

    def clear_input(self):
        self.user_input.delete("1.0", "end")

    def display_action_choices(self, choices: List[str]):
        """Display action choice buttons for the user to click."""
        # Clear any existing choice buttons
        for widget in self.choice_button_frame.winfo_children():
            widget.destroy()
        
        if not choices:
            self.choice_button_frame.grid_remove()
            return
        
        # Show the choice frame
        self.choice_button_frame.grid()
        
        # Create a button for each choice
        for i, choice in enumerate(choices):
            btn = ctk.CTkButton(
                self.choice_button_frame,
                text=f"{i+1}. {choice}",
                command=lambda c=choice: self.select_choice(c)
            )
            btn.pack(side="left", padx=5, pady=5, expand=True, fill="x")

    def select_choice(self, choice: str):
        """Handle when a user clicks an action choice."""
        # Populate the input box with the choice
        self.user_input.delete("1.0", "end")
        self.user_input.insert("1.0", choice)
        
        # Hide the choice buttons
        self.choice_button_frame.grid_remove()
        
        # Trigger the send action
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
        # Clear choice buttons when sending a message
        for widget in self.choice_button_frame.winfo_children():
            widget.destroy()
        self.choice_button_frame.grid_remove()
        
        if self.selected_session:
            self.orchestrator.plan_and_execute(self.selected_session)

    def load_game(self, session_id: int):
        self.orchestrator.load_game(session_id)
        self.chat_history.configure(state="normal")
        self.chat_history.delete("1.0", "end")
        history = self.orchestrator.session.get_history()
        for message in history:
            if message.role != "system":
                self.add_message(f"{message.role.capitalize()}: {message.content}\n")
        self.chat_history.configure(state="disabled")
        
        # Load context
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
        self.add_message("[Context saved]\n")

    def open_world_info_manager(self):
        if not self.selected_prompt:
            self.add_message("[Please select a prompt first]\n")
            return
        
        world_info_view = WorldInfoManagerView(self, self.db_manager, self.selected_prompt.id)
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
        
        # Visually indicate selection
        for widget in self.prompt_scrollable_frame.winfo_children():
            if widget.cget("text") == prompt.name:
                widget.configure(fg_color="blue")
            else:
                widget.configure(fg_color=["#3a7ebf", "#1f538d"])
        
        # Auto-collapse the prompt panel to bring sessions into view
        if self.prompt_collapsible and not self.prompt_collapsible.is_collapsed:
            self.prompt_collapsible.toggle()

    def on_session_select(self, session):
        self.selected_session = session
        self.load_game(session.id)
        self.send_button.configure(state="normal")
        
        # Set session for memory inspector
        if hasattr(self, 'memory_inspector'):
            self.memory_inspector.set_session(session.id)
        
        # Visually indicate selection
        for widget in self.session_scrollable_frame.winfo_children():
            if widget.cget("text") == session.name:
                widget.configure(fg_color="blue")
            else:
                widget.configure(fg_color=["#3a7ebf", "#1f538d"])
        
        # Auto-collapse the session panel to bring Advanced Context into view
        if self.session_collapsible and not self.session_collapsible.is_collapsed:
            self.session_collapsible.toggle()

    # Prompt CRUD methods
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