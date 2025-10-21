import customtkinter as ctk
from datetime import datetime
from app.gui.prompt_manager_view import PromptManagerView

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

        self.user_input = ctk.CTkTextbox(self.main_panel, height=100)
        self.user_input.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        button_frame = ctk.CTkFrame(self.main_panel)
        button_frame.grid(row=1, column=1, sticky="ns", padx=5, pady=5)

        self.send_button = ctk.CTkButton(button_frame, text="Send", state="disabled", command=self.handle_send_button)
        self.send_button.pack(expand=True, fill="both", padx=2, pady=2)

        self.stop_button = ctk.CTkButton(button_frame, text="Stop")
        self.stop_button.pack(expand=True, fill="both", padx=2, pady=2)


        # Control Panel
        self.control_panel = ctk.CTkFrame(self, fg_color="#2B2B2B")
        self.control_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        self.control_panel.grid_propagate(False)
        self._create_control_panel_widgets()

        self.refresh_prompt_list()
        self.refresh_session_list()


    def _create_control_panel_widgets(self):
        # Game Session Management
        session_frame = ctk.CTkFrame(self.control_panel)
        session_frame.pack(pady=10, padx=10, fill="x", expand=False)

        session_label = ctk.CTkLabel(session_frame, text="Game Sessions")
        session_label.pack()

        self.session_scrollable_frame = ctk.CTkScrollableFrame(session_frame, height=100)
        self.session_scrollable_frame.pack(pady=5, padx=5, fill="x")

        new_game_button = ctk.CTkButton(session_frame, text="New Game", command=self.new_game)
        new_game_button.pack(pady=5, padx=5, fill="x")



        # Prompt Management
        prompt_frame = ctk.CTkFrame(self.control_panel)
        prompt_frame.pack(pady=10, padx=10, fill="x", expand=False)

        prompt_label = ctk.CTkLabel(prompt_frame, text="Prompt Management")
        prompt_label.pack()

        self.prompt_scrollable_frame = ctk.CTkScrollableFrame(prompt_frame, height=100)
        self.prompt_scrollable_frame.pack(pady=5, padx=5, fill="x")

        manage_prompts_button = ctk.CTkButton(prompt_frame, text="Manage Prompts", command=self.open_prompt_manager)
        manage_prompts_button.pack(pady=5, padx=5, fill="x")

        # LLM Parameters
        llm_frame = ctk.CTkFrame(self.control_panel)
        llm_frame.pack(pady=10, padx=10, fill="x", expand=False)

        llm_label = ctk.CTkLabel(llm_frame, text="LLM Parameters")
        llm_label.pack()

        self.provider_selector = ctk.CTkOptionMenu(llm_frame, values=["Gemini", "OpenAI"])
        self.provider_selector.pack(pady=5, padx=5, fill="x")

        self.temperature_slider = ctk.CTkSlider(llm_frame)
        self.temperature_slider.pack(pady=5, padx=5, fill="x")

        self.top_p_slider = ctk.CTkSlider(llm_frame)
        self.top_p_slider.pack(pady=5, padx=5, fill="x")

        # Game State Inspector
        inspector_frame = ctk.CTkFrame(self.control_panel)
        inspector_frame.pack(pady=10, padx=10, fill="both", expand=True)

        inspector_tabs = ctk.CTkTabview(inspector_frame)
        inspector_tabs.pack(fill="both", expand=True)
        inspector_tabs.add("Characters")
        inspector_tabs.add("Inventory")
        inspector_tabs.add("Quests")


    def add_message(self, message: str):
        self.chat_history.configure(state="normal")
        self.chat_history.insert("end", message)
        self.chat_history.configure(state="disabled")
        self.chat_history.see("end")

    def get_input(self) -> str:
        return self.user_input.get("1.0", "end-1c")

    def clear_input(self):
        self.user_input.delete("1.0", "end")

    def open_prompt_manager(self, _=None):
        prompt_manager_view = PromptManagerView(self, self.db_manager, on_close_callback=self.refresh_prompt_list)
        prompt_manager_view.grab_set()

    def new_game(self):
        if not self.selected_prompt:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        session_name = f"{timestamp}_{self.selected_prompt.name}"

        self.orchestrator.new_session(self.selected_prompt.content)
        self.orchestrator.save_game(session_name, self.selected_prompt.id)
        self.refresh_session_list(self.selected_prompt.id)


    def handle_send_button(self):
        if self.selected_session:
            self.orchestrator.handle_send(self.selected_session)

    def load_game(self, session_id: int):
        self.orchestrator.load_game(session_id)
        self.chat_history.configure(state="normal")
        self.chat_history.delete("1.0", "end")
        history = self.orchestrator.session.get_history()
        for message in history:
            if message.role != "system":
                self.add_message(f"{message.role.capitalize()}: {message.content}\n")
        self.chat_history.configure(state="disabled")

    def refresh_session_list(self, prompt_id: int | None = None):
        for widget in self.session_scrollable_frame.winfo_children():
            widget.destroy()

        if prompt_id:
            sessions = self.db_manager.get_sessions_by_prompt(prompt_id)
            for session in sessions:
                btn = ctk.CTkButton(self.session_scrollable_frame, text=session.name,
                                    command=lambda s=session: self.on_session_select(s))
                btn.pack(pady=2, padx=5, fill="x")

    def refresh_prompt_list(self):
        for widget in self.prompt_scrollable_frame.winfo_children():
            widget.destroy()
            
        prompts = self.db_manager.get_all_prompts()
        
        # Ensure "Default" prompt exists
        default_prompt = next((p for p in prompts if p.name == "Default"), None)
        if not default_prompt:
            with open("prompts/default.txt", "r") as f:
                default_prompt_content = f.read()
            default_prompt = self.db_manager.create_prompt("Default", default_prompt_content)
            prompts.insert(0, default_prompt)

        for prompt in prompts:
            btn = ctk.CTkButton(self.prompt_scrollable_frame, text=prompt.name,
                                command=lambda p=prompt: self.on_prompt_select(p))
            btn.pack(pady=2, padx=5, fill="x")

    def on_prompt_select(self, prompt):
        self.selected_prompt = prompt
        self.selected_session = None # Clear session selection
        self.send_button.configure(state="disabled")
        self.refresh_session_list(prompt.id)
        # Visually indicate selection (optional, but good UX)
        for widget in self.prompt_scrollable_frame.winfo_children():
            if widget.cget("text") == prompt.name:
                widget.configure(fg_color="blue")
            else:
                widget.configure(fg_color=["#3a7ebf", "#1f538d"]) # Default colors

    def on_session_select(self, session):
        self.selected_session = session
        self.load_game(session.id)
        self.send_button.configure(state="normal")
        # Visually indicate selection
        for widget in self.session_scrollable_frame.winfo_children():
            if widget.cget("text") == session.name:
                widget.configure(fg_color="blue")
            else:
                widget.configure(fg_color=["#3a7ebf", "#1f538d"])