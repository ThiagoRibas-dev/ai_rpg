import customtkinter as ctk

class PromptManagerView(ctk.CTkToplevel):
    def __init__(self, master, db_manager, on_close_callback=None):
        super().__init__(master)
        self.db_manager = db_manager
        self.on_close_callback = on_close_callback

        self.title("Prompt Manager")
        self.geometry("600x400")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.prompts_list = ctk.CTkTextbox(self, state="disabled")
        self.prompts_list.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

        self.new_button = ctk.CTkButton(self, text="New", command=self.new_prompt)
        self.new_button.grid(row=1, column=0, padx=10, pady=10)

        self.edit_button = ctk.CTkButton(self, text="Edit", command=self.edit_prompt)
        self.edit_button.grid(row=1, column=1, padx=10, pady=10)

        self.delete_button = ctk.CTkButton(self, text="Delete", command=self.delete_prompt)
        self.delete_button.grid(row=1, column=2, padx=10, pady=10)

        self.refresh_prompts()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()

    def refresh_prompts(self):
        self.prompts_list.configure(state="normal")
        self.prompts_list.delete("1.0", "end")
        prompts = self.db_manager.get_all_prompts()
        for prompt in prompts:
            self.prompts_list.insert("end", f"{prompt.id}: {prompt.name}\n")
        self.prompts_list.configure(state="disabled")

    def new_prompt(self):
        dialog = ctk.CTkInputDialog(text="Enter prompt name:", title="New Prompt")
        name = dialog.get_input()
        if name:
            content_dialog = ctk.CTkInputDialog(text="Enter prompt content:", title="New Prompt")
            content = content_dialog.get_input()
            if content:
                self.db_manager.create_prompt(name, content)
                self.refresh_prompts()

    def edit_prompt(self):
        dialog = ctk.CTkInputDialog(text="Enter prompt ID to edit:", title="Edit Prompt")
        prompt_id_str = dialog.get_input()
        if prompt_id_str and prompt_id_str.isdigit():
            prompt_id = int(prompt_id_str)
            prompts = self.db_manager.get_all_prompts()
            prompt = next((p for p in prompts if p.id == prompt_id), None)
            if prompt:
                name_dialog = ctk.CTkInputDialog(text="Enter new name:", title="Edit Prompt")
                name = name_dialog.get_input()
                content_dialog = ctk.CTkInputDialog(text="Enter new content:", title="Edit Prompt")
                content = content_dialog.get_input()
                if name and content:
                    prompt.name = name
                    prompt.content = content
                    self.db_manager.update_prompt(prompt)
                    self.refresh_prompts()

    def delete_prompt(self):
        dialog = ctk.CTkInputDialog(text="Enter prompt ID to delete:", title="Delete Prompt")
        prompt_id_str = dialog.get_input()
        if prompt_id_str and prompt_id_str.isdigit():
            prompt_id = int(prompt_id_str)
            self.db_manager.delete_prompt(prompt_id)
            self.refresh_prompts()
