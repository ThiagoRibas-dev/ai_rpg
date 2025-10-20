import customtkinter as ctk
from app.gui.prompt_manager_view import PromptManagerView

class MainView(ctk.CTk):
    def __init__(self, db_manager):
        super().__init__()

        self.db_manager = db_manager
        self.title("AI-RPG")
        self.geometry("800x600")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.textbox = ctk.CTkTextbox(self, state="disabled")
        self.textbox.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.entry = ctk.CTkEntry(self, placeholder_text="Type your message here...")
        self.entry.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.send_button = ctk.CTkButton(self, text="Send")
        self.send_button.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(0, 10))

        self.menubar = ctk.CTkFrame(self, height=30)
        self.menubar.grid(row=0, column=0, columnspan=2, sticky="new")

        self.prompt_menu = ctk.CTkOptionMenu(self.menubar, values=["Manage Prompts"], command=self.open_prompt_manager)
        self.prompt_menu.pack(side="left", padx=5)

        self.new_game_button = ctk.CTkButton(self.menubar, text="New Game", command=self.new_game)
        self.new_game_button.pack(side="left", padx=5)

        self.save_game_button = ctk.CTkButton(self.menubar, text="Save Game", command=self.save_game)
        self.save_game_button.pack(side="left", padx=5)

        self.load_game_button = ctk.CTkButton(self.menubar, text="Load Game", command=self.load_game)
        self.load_game_button.pack(side="left", padx=5)

    def add_message(self, message: str):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", message)
        self.textbox.configure(state="disabled")
        self.textbox.see("end")

    def get_input(self) -> str:
        return self.entry.get()

    def clear_input(self):
        self.entry.delete(0, "end")

    def open_prompt_manager(self, _=None):
        prompt_manager_view = PromptManagerView(self, self.db_manager)
        prompt_manager_view.grab_set()

    def new_game(self):
        prompts = self.db_manager.get_all_prompts()
        prompt_names = [prompt.name for prompt in prompts]
        prompt_names.insert(0, "Default")

        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("end", "Available Prompts:\n\n")
        for name in prompt_names:
            self.textbox.insert("end", f"- {name}\n")
        self.textbox.configure(state="disabled")

        dialog = ctk.CTkInputDialog(text="Type the name of the prompt to start a new game:", title="New Game")
        prompt_name = dialog.get_input()

        if prompt_name and prompt_name in prompt_names:
            # A bit inefficient to fetch them all again, but fine for now.
            selected_prompt = next((p for p in prompts if p.name == prompt_name), None)
            if selected_prompt:
                self.orchestrator.new_session(selected_prompt.content)
            elif prompt_name == "Default":
                with open("prompts/default.txt", "r") as f:
                    self.orchestrator.new_session(f.read())

            self.textbox.configure(state="normal")
            self.textbox.delete("1.0", "end")
            self.textbox.configure(state="disabled")

    def save_game(self):
        dialog = ctk.CTkInputDialog(text="Enter a name for your save:", title="Save Game")
        save_name = dialog.get_input()
        if save_name:
            self.orchestrator.save_game(save_name)

    def load_game(self):
        sessions = self.db_manager.get_all_sessions()
        session_names = [session.name for session in sessions]
        if not session_names:
            return

        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("end", "Available Saved Games:\n\n")
        for name in session_names:
            self.textbox.insert("end", f"- {name}\n")
        self.textbox.configure(state="disabled")

        dialog = ctk.CTkInputDialog(text="Type the name of the game to load:", title="Load Game")
        session_name = dialog.get_input()

        if session_name and session_name in session_names:
            selected_session = next((s for s in sessions if s.name == session_name), None)
            if selected_session:
                self.orchestrator.load_game(selected_session.id)
                self.textbox.configure(state="normal")
                self.textbox.delete("1.0", "end")
                history = self.orchestrator.session.get_history()
                for message in history:
                    if message.role != "system":
                        self.add_message(f"{message.role.capitalize()}: {message.content}\n")
                self.textbox.configure(state="disabled")