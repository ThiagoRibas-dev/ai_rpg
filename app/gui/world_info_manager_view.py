import customtkinter as ctk
from app.models.world_info import WorldInfo


class WorldInfoManagerView(ctk.CTkToplevel):
    def __init__(self, master, db_manager, prompt_id: int, vector_store=None):
        super().__init__(master)
        self.db_manager = db_manager
        self.prompt_id = prompt_id
        self.vector_store = vector_store
        self.selected_world_info = None

        self.title("World Info Manager")
        self.geometry("800x600")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # Left panel - List of world info entries
        left_panel = ctk.CTkFrame(self)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        list_label = ctk.CTkLabel(
            left_panel, text="World Info Entries", font=("Arial", 16, "bold")
        )
        list_label.pack(pady=10)

        self.world_info_listbox = ctk.CTkScrollableFrame(left_panel)
        self.world_info_listbox.pack(fill="both", expand=True, padx=5, pady=5)

        button_frame = ctk.CTkFrame(left_panel)
        button_frame.pack(fill="x", padx=5, pady=5)

        new_button = ctk.CTkButton(
            button_frame, text="New", command=self.new_world_info
        )
        new_button.pack(side="left", padx=2, expand=True, fill="x")

        delete_button = ctk.CTkButton(
            button_frame, text="Delete", command=self.delete_world_info
        )
        delete_button.pack(side="left", padx=2, expand=True, fill="x")

        # Right panel - Edit world info
        right_panel = ctk.CTkFrame(self)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)

        edit_label = ctk.CTkLabel(
            right_panel, text="Edit Entry", font=("Arial", 16, "bold")
        )
        edit_label.pack(pady=10)

        keywords_label = ctk.CTkLabel(right_panel, text="Keywords (comma-separated):")
        keywords_label.pack(pady=(10, 0), padx=10, anchor="w")

        self.keywords_entry = ctk.CTkEntry(right_panel)
        self.keywords_entry.pack(fill="x", padx=10, pady=5)

        content_label = ctk.CTkLabel(right_panel, text="Content:")
        content_label.pack(pady=(10, 0), padx=10, anchor="w")

        self.content_textbox = ctk.CTkTextbox(right_panel)
        self.content_textbox.pack(fill="both", expand=True, padx=10, pady=5)

        save_button = ctk.CTkButton(
            right_panel, text="Save Changes", command=self.save_world_info
        )
        save_button.pack(pady=10, padx=10, fill="x")

        self.refresh_list()

    def refresh_list(self):
        """Refresh the list of world info entries."""
        for widget in self.world_info_listbox.winfo_children():
            widget.destroy()

        world_infos = self.db_manager.world_info.get_by_prompt(self.prompt_id)

        for wi in world_infos:
            # Create a frame for each entry
            frame = ctk.CTkFrame(self.world_info_listbox)
            frame.pack(fill="x", padx=5, pady=2)

            # Display keywords as a button
            btn = ctk.CTkButton(
                frame,
                text=wi.keywords[:40] + ("..." if len(wi.keywords) > 40 else ""),
                command=lambda w=wi: self.select_world_info(w),
            )
            btn.pack(fill="x")

    def select_world_info(self, world_info: WorldInfo):
        """Load a world info entry for editing."""
        self.selected_world_info = world_info

        self.keywords_entry.delete(0, "end")
        self.keywords_entry.insert(0, world_info.keywords)

        self.content_textbox.delete("1.0", "end")
        self.content_textbox.insert("1.0", world_info.content)

        # Highlight selection
        for widget in self.world_info_listbox.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ctk.CTkButton):
                    if child.cget("text").startswith(world_info.keywords[:40]):
                        child.configure(fg_color="blue")
                    else:
                        child.configure(fg_color=["#3a7ebf", "#1f538d"])

    def new_world_info(self):
        """Create a new world info entry."""
        wi = self.db_manager.world_info.create(self.prompt_id, "New Entry", "")
        if self.vector_store:
            try:
                self.vector_store.upsert_world_info(self.prompt_id, wi.id, wi.content)
            except Exception:
                pass
        self.refresh_list()
        self.select_world_info(wi)

    def save_world_info(self):
        """Save changes to the selected world info entry."""
        if not self.selected_world_info:
            return

        keywords = self.keywords_entry.get()
        content = self.content_textbox.get("1.0", "end-1c")

        self.selected_world_info.keywords = keywords
        self.selected_world_info.content = content

        self.db_manager.world_info.update(self.selected_world_info)
        if self.vector_store:
            try:
                self.vector_store.upsert_world_info(
                    self.prompt_id, self.selected_world_info.id, content
                )
            except Exception:
                pass
        self.refresh_list()

    def delete_world_info(self):
        """Delete the selected world info entry."""
        if not self.selected_world_info:
            return

        self.db_manager.world_info.delete(self.selected_world_info.id)
        if self.vector_store:
            try:
                self.vector_store.delete_world_info(
                    self.prompt_id, self.selected_world_info.id
                )
            except Exception:
                pass
        self.selected_world_info = None

        self.keywords_entry.delete(0, "end")
        self.content_textbox.delete("1.0", "end")

        self.refresh_list()
