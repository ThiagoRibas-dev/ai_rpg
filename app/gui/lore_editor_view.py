import customtkinter as ctk
from app.models.memory import Memory
from typing import Optional


class LoreEditorView(ctk.CTkToplevel):
    """A player-facing editor for memories of the 'lore' kind."""
    def __init__(self, master, db_manager, session_id: int, vector_store=None):
        super().__init__(master)
        self.db_manager = db_manager
        self.session_id = session_id
        self.vector_store = vector_store
        self.selected_memory: Optional[Memory] = None

        self.title("Lorebook Editor")
        self.geometry("800x600")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # Left panel - List of lore entries
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
            button_frame, text="New Entry", command=self.new_lore_entry
        )
        new_button.pack(side="left", padx=2, expand=True, fill="x")

        delete_button = ctk.CTkButton(
            button_frame, text="Delete", command=self.delete_lore_entry, fg_color="darkred"
        )
        delete_button.pack(side="left", padx=2, expand=True, fill="x")

        # Right panel - Edit lore entry
        right_panel = ctk.CTkFrame(self)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)

        edit_label = ctk.CTkLabel(
            right_panel, text="Edit Entry", font=("Arial", 16, "bold")
        )
        edit_label.pack(pady=10)

        tags_label = ctk.CTkLabel(right_panel, text="Tags (comma-separated):")
        tags_label.pack(pady=(10, 0), padx=10, anchor="w")

        self.tags_entry = ctk.CTkEntry(right_panel)
        self.tags_entry.pack(fill="x", padx=10, pady=5)

        priority_label = ctk.CTkLabel(right_panel, text="Priority (Importance):")
        priority_label.pack(pady=(10, 0), padx=10, anchor="w")

        self.priority_slider = ctk.CTkSlider(right_panel, from_=1, to=5, number_of_steps=4)
        self.priority_slider.pack(fill="x", padx=10, pady=5)
        self.priority_slider.set(3)

        content_label = ctk.CTkLabel(right_panel, text="Content:")
        content_label.pack(pady=(10, 0), padx=10, anchor="w")

        self.content_textbox = ctk.CTkTextbox(right_panel)
        self.content_textbox.pack(fill="both", expand=True, padx=10, pady=5)

        save_button = ctk.CTkButton(
            right_panel, text="Save Changes", command=self.save_lore_entry
        )
        save_button.pack(pady=10, padx=10, fill="x")

        self.refresh_list()

    def refresh_list(self):
        """Refresh the list of lore entries."""
        for widget in self.world_info_listbox.winfo_children():
            widget.destroy()

        # Query memories of kind 'lore' for the current session
        lore_entries = self.db_manager.memories.query(self.session_id, kind="lore", limit=200)

        for lore in lore_entries:
            # Create a frame for each entry
            frame = ctk.CTkFrame(self.world_info_listbox)
            frame.pack(fill="x", padx=5, pady=2)

            # Use first few words of content as title
            title = lore.content[:40] + ("..." if len(lore.content) > 40 else "")

            # Display keywords as a button
            btn = ctk.CTkButton(
                frame,
                text=title,
                command=lambda lore_entry=lore: self.select_lore_entry(lore_entry),
            )
            btn.pack(fill="x")

    def select_lore_entry(self, memory: Memory):
        """Load a lore memory for editing."""
        self.selected_memory = memory

        self.tags_entry.delete(0, "end")
        self.tags_entry.insert(0, ", ".join(memory.tags_list()))

        self.priority_slider.set(memory.priority)

        self.content_textbox.delete("1.0", "end")
        self.content_textbox.insert("1.0", memory.content)

        # Highlight selection
        for widget in self.world_info_listbox.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ctk.CTkButton):
                    if child.cget("text").startswith(memory.content[:40]):
                        child.configure(fg_color="blue")
                    else:
                        child.configure(fg_color=["#3a7ebf", "#1f538d"])

    def new_lore_entry(self):
        """Create a new lore memory."""
        new_mem = self.db_manager.memories.create(
            session_id=self.session_id,
            kind="lore",
            content="New Lore Entry - Edit Me",
            priority=3,
            tags=["new"]
        )
        self.refresh_list()
        self.select_lore_entry(new_mem)

    def save_lore_entry(self):
        """Save changes to the selected lore memory."""
        if not self.selected_memory:
            return

        tags_str = self.tags_entry.get()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        priority = int(self.priority_slider.get())
        content = self.content_textbox.get("1.0", "end-1c")

        updated_mem = self.db_manager.memories.update(
            memory_id=self.selected_memory.id,
            content=content,
            priority=priority,
            tags=tags
        )
        
        if self.vector_store:
            try:
                self.vector_store.upsert_memory(
                    self.session_id, updated_mem.id, updated_mem.content, "lore", tags, priority
                )
            except Exception:
                pass
        self.refresh_list()

    def delete_lore_entry(self):
        """Delete the selected lore memory."""
        if not self.selected_memory:
            return

        self.db_manager.memories.delete(self.selected_memory.id)
        if self.vector_store:
            try:
                self.vector_store.delete_memory(
                    self.session_id, self.selected_memory.id
                )
            except Exception:
                pass
        self.selected_memory = None

        self.tags_entry.delete(0, "end")
        self.content_textbox.delete("1.0", "end")

        self.refresh_list()
