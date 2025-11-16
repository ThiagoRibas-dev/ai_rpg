# File: app/gui/panels/dialogs/memory_detail_dialog.py
# --- NEW FILE ---

import customtkinter as ctk

class MemoryDetailDialog(ctk.CTkToplevel):
    """Dialog for viewing and editing a single memory."""

    def __init__(self, parent, db_manager, memory, on_save_callback):
        super().__init__(parent)

        self.db_manager = db_manager
        self.memory = memory
        self.on_save_callback = on_save_callback

        self.title(f"Memory ID: {memory.id}")
        self.geometry("600x500")
        self.grab_set()  # Make modal

        self._create_widgets()
        self._load_memory_data()

    def _create_widgets(self):
        # Kind selector
        kind_frame = ctk.CTkFrame(self)
        kind_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(kind_frame, text="Kind:").pack(side="left", padx=5)
        self.kind_menu = ctk.CTkOptionMenu(
            kind_frame, values=["episodic", "semantic", "lore", "user_pref"]
        )
        self.kind_menu.pack(side="left", padx=5)

        # Priority slider
        priority_frame = ctk.CTkFrame(self)
        priority_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(priority_frame, text="Priority:").pack(side="left", padx=5)
        self.priority_slider = ctk.CTkSlider(
            priority_frame, from_=1, to=5, number_of_steps=4
        )
        self.priority_slider.pack(side="left", padx=5, fill="x", expand=True)

        self.priority_label = ctk.CTkLabel(priority_frame, text="3")
        self.priority_label.pack(side="left", padx=5)

        self.priority_slider.configure(command=self._update_priority_label)

        # Tags entry
        tags_frame = ctk.CTkFrame(self)
        tags_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(tags_frame, text="Tags (comma-separated):").pack(
            anchor="w", padx=5
        )
        self.tags_entry = ctk.CTkEntry(tags_frame)
        self.tags_entry.pack(fill="x", padx=5, pady=5)

        # Content textbox
        content_frame = ctk.CTkFrame(self)
        content_frame.pack(fill="both", expand=True, padx=10, pady=5)

        ctk.CTkLabel(content_frame, text="Content:").pack(anchor="w", padx=5)
        self.content_textbox = ctk.CTkTextbox(content_frame)
        self.content_textbox.pack(fill="both", expand=True, padx=5, pady=5)

        # Metadata display
        meta_frame = ctk.CTkFrame(self)
        meta_frame.pack(fill="x", padx=10, pady=5)

        self.meta_label = ctk.CTkLabel(
            meta_frame, text="", text_color="gray", font=("Arial", 10)
        )
        self.meta_label.pack(padx=5, pady=5)

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=10, pady=10)

        save_btn = ctk.CTkButton(button_frame, text="Save", command=self.save_memory)
        save_btn.pack(side="left", padx=5, expand=True, fill="x")

        cancel_btn = ctk.CTkButton(button_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side="left", padx=5, expand=True, fill="x")

    def _update_priority_label(self, value):
        """Update the priority label when slider changes."""
        priority = int(value)
        self.priority_label.configure(text=str(priority))

    def _load_memory_data(self):
        """Load memory data into the form fields."""
        self.kind_menu.set(self.memory.kind)
        self.priority_slider.set(self.memory.priority)
        self._update_priority_label(self.memory.priority)

        tags_str = ", ".join(self.memory.tags_list())
        self.tags_entry.insert(0, tags_str)

        self.content_textbox.insert("1.0", self.memory.content)

        # Metadata
        meta_text = f"Created: {self.memory.created_at} | Access Count: {self.memory.access_count}"
        if self.memory.last_accessed:
            meta_text += f" | Last Accessed: {self.memory.last_accessed}"
        self.meta_label.configure(text=meta_text)

    def save_memory(self):
        """Save changes to the memory."""
        new_kind = self.kind_menu.get()
        new_priority = int(self.priority_slider.get())
        new_content = self.content_textbox.get("1.0", "end-1c")

        tags_str = self.tags_entry.get()
        new_tags = [t.strip() for t in tags_str.split(",") if t.strip()]

        # Update in database
        self.db_manager.memories.update(
            self.memory.id,
            kind=new_kind,
            content=new_content,
            priority=new_priority,
            tags=new_tags,
        )

        if self.on_save_callback:
            self.on_save_callback()

        self.destroy()
