import customtkinter as ctk
from typing import Optional
from app.gui.panels.dialogs.memory_detail_dialog import MemoryDetailDialog
from app.gui.panels.inspectors.inspector_utils import create_memory_card


class MemoryInspectorView(ctk.CTkFrame):
    """
    A panel for viewing, searching, and managing AI-generated memories.
    """

    def __init__(self, parent, db_manager, orchestrator):
        super().__init__(parent)

        self.db_manager = db_manager
        self.orchestrator = orchestrator
        self.current_session_id: Optional[int] = None
        self.selected_memory_id: Optional[int] = None
        self.filter_kind: str = "All"
        self.search_query: str = ""

        self._create_widgets()

    def _create_widgets(self):
        # Statistics panel (NEW - at the top)
        stats_panel = ctk.CTkFrame(self)
        stats_panel.pack(fill="x", padx=5, pady=5)

        self.total_label = ctk.CTkLabel(stats_panel, text="Total: 0")
        self.total_label.pack(side="left", padx=10)

        self.episodic_label = ctk.CTkLabel(stats_panel, text="📖 0")
        self.episodic_label.pack(side="left", padx=5)

        self.semantic_label = ctk.CTkLabel(stats_panel, text="💡 0")
        self.semantic_label.pack(side="left", padx=5)

        self.lore_label = ctk.CTkLabel(stats_panel, text="📜 0")
        self.lore_label.pack(side="left", padx=5)

        self.user_pref_label = ctk.CTkLabel(stats_panel, text="⚙️ 0")
        self.user_pref_label.pack(side="left", padx=5)

        # Top controls: filters and search
        control_frame = ctk.CTkFrame(self)
        control_frame.pack(fill="x", padx=5, pady=5)

        # Filter by kind
        ctk.CTkLabel(control_frame, text="Filter:").pack(side="left", padx=5)
        self.kind_filter = ctk.CTkOptionMenu(
            control_frame,
            values=["All", "Episodic", "Semantic", "Lore", "User Pref"],
            command=self.on_filter_changed,
        )
        self.kind_filter.pack(side="left", padx=5)

        # Search box
        ctk.CTkLabel(control_frame, text="Search:").pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(
            control_frame, placeholder_text="Search content or tags..."
        )
        self.search_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", lambda e: self.on_search_changed())

        # Refresh button
        refresh_btn = ctk.CTkButton(
            control_frame, text="↻", width=40, command=self.refresh_memories
        )
        refresh_btn.pack(side="left", padx=5)

        # Memory list (scrollable)
        self.memory_list_frame = ctk.CTkScrollableFrame(self, label_text="Memories")
        self.memory_list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Bottom buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=5, pady=5)

        new_btn = ctk.CTkButton(
            button_frame, text="New Memory", command=self.create_memory
        )
        new_btn.pack(side="left", padx=2, expand=True, fill="x")

        export_btn = ctk.CTkButton(
            button_frame, text="Export", command=self.export_memories
        )
        export_btn.pack(side="left", padx=2, expand=True, fill="x")

        import_btn = ctk.CTkButton(
            button_frame, text="Import", command=self.import_memories
        )
        import_btn.pack(side="left", padx=2, expand=True, fill="x")

        clear_btn = ctk.CTkButton(
            button_frame,
            text="Clear All",
            command=self.clear_all_memories,
            fg_color="darkred",
            hover_color="red",
        )
        clear_btn.pack(side="left", padx=2, expand=True, fill="x")

    def set_session(self, session_id: int):
        """Set the current session and refresh the memory list."""
        self.current_session_id = session_id
        self.refresh_memories()

    def refresh_memories(self):
        """Refresh the memory list from the database."""
        if not self.current_session_id:
            return

        # Get all memories for session
        all_memories = self.db_manager.memories.get_by_session(self.current_session_id)

        # Apply filters
        filtered_memories = []
        for mem in all_memories:
            # Kind filter
            if self.filter_kind != "All":
                if mem.kind.title() != self.filter_kind:
                    continue

            # Search filter
            if self.search_query:
                search_text = (mem.content + " " + " ".join(mem.tags_list())).lower()
                if self.search_query.lower() not in search_text:
                    continue

            filtered_memories.append(mem)

        # Update statistics
        stats = self.db_manager.memories.get_statistics(self.current_session_id)
        self.total_label.configure(text=f"Total: {stats['total']}")
        by_kind = stats.get("by_kind", {})
        self.episodic_label.configure(text=f"📖 {by_kind.get('episodic', 0)}")
        self.semantic_label.configure(text=f"💡 {by_kind.get('semantic', 0)}")
        self.lore_label.configure(text=f"📜 {by_kind.get('lore', 0)}")
        self.user_pref_label.configure(text=f"⚙️ {by_kind.get('user_pref', 0)}")

        # Clear and rebuild list
        for widget in self.memory_list_frame.winfo_children():
            widget.destroy()

        if not filtered_memories:
            no_mem_label = ctk.CTkLabel(
                self.memory_list_frame, text="No memories found", text_color="gray"
            )
            no_mem_label.pack(pady=20)
            return

        # Display memories
        for mem in filtered_memories:
            callbacks = {
                'on_view': self.view_memory_detail,
                'on_delete': self.delete_memory
            }
            create_memory_card(self.memory_list_frame, mem, callbacks)

    def on_filter_changed(self, value: str):
        """Handle filter dropdown change."""
        self.filter_kind = value
        self.refresh_memories()

    def on_search_changed(self):
        """Handle search box change."""
        self.search_query = self.search_entry.get()
        self.refresh_memories()

    def view_memory_detail(self, memory):
        """Open a dialog to view and edit memory details."""
        MemoryDetailDialog(self, self.db_manager, memory, self.refresh_memories)

    def delete_memory(self, memory):
        """Delete a memory with confirmation."""
        dialog = ctk.CTkInputDialog(
            text=f"Delete memory ID {memory.id}?\nType 'DELETE' to confirm:",
            title="Confirm Delete",
        )
        result = dialog.get_input()

        if result == "DELETE":
            self.db_manager.memories.delete(memory.id)
            self.refresh_memories()

    def create_memory(self):
        """Manually create a new memory."""
        if not self.current_session_id:
            return

        # Create a blank memory
        memory = self.db_manager.memories.create(
            session_id=self.current_session_id,
            kind="semantic",
            content="New memory - click to edit",
            priority=3,
            tags=[],
        )

        self.refresh_memories()
        self.view_memory_detail(memory)

    def export_memories(self):
        """Export memories to a JSON file."""
        if not self.current_session_id:
            return

        import json
        from tkinter import filedialog

        memories = self.db_manager.memories.get_by_session(self.current_session_id)

        export_data = []
        for mem in memories:
            export_data.append(
                {
                    "kind": mem.kind,
                    "content": mem.content,
                    "priority": mem.priority,
                    "tags": mem.tags_list(),
                    "created_at": mem.created_at,
                }
            )

        filepath = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON files", "*.json")]
        )

        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

    def import_memories(self):
        """Import memories from a JSON file."""
        if not self.current_session_id:
            return

        import json
        from tkinter import filedialog

        filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])

        if not filepath:
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                import_data = json.load(f)

            for mem_data in import_data:
                self.db_manager.memories.create(
                    session_id=self.current_session_id,
                    kind=mem_data.get("kind", "semantic"),
                    content=mem_data.get("content", ""),
                    priority=mem_data.get("priority", 3),
                    tags=mem_data.get("tags", []),
                )

            self.refresh_memories()
        except (json.JSONDecodeError, IOError, KeyError) as e:
            print(f"Import failed: {e}")

    def clear_all_memories(self):
        """Delete all memories for the current session."""
        if not self.current_session_id:
            return

        dialog = ctk.CTkInputDialog(
            text="This will delete ALL memories for this session!\nType 'DELETE ALL' to confirm:",
            title="Confirm Clear All",
        )
        result = dialog.get_input()

        if result == "DELETE ALL":
            memories = self.db_manager.memories.get_by_session(self.current_session_id)
            for mem in memories:
                self.db_manager.memories.delete(mem.id)
            self.refresh_memories()
