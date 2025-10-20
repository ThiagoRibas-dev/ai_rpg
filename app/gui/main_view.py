import customtkinter as ctk

class MainView(ctk.CTk):
    def __init__(self):
        super().__init__()

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

    def add_message(self, message: str):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", message)
        self.textbox.configure(state="disabled")
        self.textbox.see("end")

    def get_input(self) -> str:
        return self.entry.get()

    def clear_input(self):
        self.entry.delete(0, "end")