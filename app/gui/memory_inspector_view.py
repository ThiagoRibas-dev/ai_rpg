import customtkinter as ctk
from typing import Optional
from datetime import datetime

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
            command=self.on_filter_changed
        )
        self.kind_filter.pack(side="left", padx=5)
        
        # Search box
        ctk.CTkLabel(control_frame, text="Search:").pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(control_frame, placeholder_text="Search content or tags...")
        self.search_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", lambda e: self.on_search_changed())
        
        # Refresh button
        refresh_btn = ctk.CTkButton(control_frame, text="↻", width=40, command=self.refresh_memories)
        refresh_btn.pack(side="left", padx=5)
        
        # Memory list (scrollable)
        self.memory_list_frame = ctk.CTkScrollableFrame(self, label_text="Memories")
        self.memory_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Bottom buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        new_btn = ctk.CTkButton(button_frame, text="New Memory", command=self.create_memory)
        new_btn.pack(side="left", padx=2, expand=True, fill="x")
        
        export_btn = ctk.CTkButton(button_frame, text="Export", command=self.export_memories)
        export_btn.pack(side="left", padx=2, expand=True, fill="x")
        
        import_btn = ctk.CTkButton(button_frame, text="Import", command=self.import_memories)
        import_btn.pack(side="left", padx=2, expand=True, fill="x")
        
        clear_btn = ctk.CTkButton(
            button_frame, 
            text="Clear All", 
            command=self.clear_all_memories,
            fg_color="darkred",
            hover_color="red"
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
        all_memories = self.db_manager.get_memories_by_session(self.current_session_id)
        
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
        stats = self.db_manager.get_memory_statistics(self.current_session_id)
        self.total_label.configure(text=f"Total: {stats['total']}")
        by_kind = stats.get('by_kind', {})
        self.episodic_label.configure(text=f"📖 {by_kind.get('episodic', 0)}")
        self.semantic_label.configure(text=f"💡 {by_kind.get('semantic', 0)}")
        self.lore_label.configure(text=f"📜 {by_kind.get('lore', 0)}")
        self.user_pref_label.configure(text=f"⚙️ {by_kind.get('user_pref', 0)}")
        
        # Clear and rebuild list
        for widget in self.memory_list_frame.winfo_children():
            widget.destroy()
        
        if not filtered_memories:
            no_mem_label = ctk.CTkLabel(
                self.memory_list_frame, 
                text="No memories found",
                text_color="gray"
            )
            no_mem_label.pack(pady=20)
            return
        
        # Display memories
        for mem in filtered_memories:
            self._create_memory_card(mem)
    
    def _create_memory_card(self, memory):
        """Create a visual card for a single memory."""
        # Card frame
        card = ctk.CTkFrame(self.memory_list_frame, border_width=2)
        card.pack(fill="x", padx=5, pady=5)
        
        # Header row
        header = ctk.CTkFrame(card)
        header.pack(fill="x", padx=5, pady=5)
        
        # Kind badge
        kind_colors = {
            "episodic": "#3498db",
            "semantic": "#2ecc71",
            "lore": "#9b59b6",
            "user_pref": "#e67e22"
        }
        kind_badge = ctk.CTkLabel(
            header,
            text=memory.kind.upper(),
            fg_color=kind_colors.get(memory.kind, "gray"),
            corner_radius=5,
            width=80
        )
        kind_badge.pack(side="left", padx=2)
        
        # Priority stars
        priority_str = "★" * memory.priority + "☆" * (5 - memory.priority)
        priority_label = ctk.CTkLabel(header, text=priority_str)
        priority_label.pack(side="left", padx=5)
        
        # ID
        id_label = ctk.CTkLabel(header, text=f"ID: {memory.id}", text_color="gray")
        id_label.pack(side="right", padx=5)
        
        # Access count
        access_label = ctk.CTkLabel(
            header, 
            text=f"↻ {memory.access_count}",
            text_color="gray"
        )
        access_label.pack(side="right", padx=5)
        
        # Content
        content_preview = memory.content[:150] + ("..." if len(memory.content) > 150 else "")
        content_label = ctk.CTkLabel(
            card,
            text=content_preview,
            wraplength=400,
            justify="left",
            anchor="w"
        )
        content_label.pack(fill="x", padx=10, pady=5)
        
        # Tags
        if memory.tags_list():
            tags_frame = ctk.CTkFrame(card)
            tags_frame.pack(fill="x", padx=10, pady=5)
            
            for tag in memory.tags_list():
                tag_label = ctk.CTkLabel(
                    tags_frame,
                    text=f"#{tag}",
                    fg_color="gray30",
                    corner_radius=3
                )
                tag_label.pack(side="left", padx=2)
        
        # Created date
        try:
            created = datetime.fromisoformat(memory.created_at)
            date_str = created.strftime("%Y-%m-%d %H:%M")
        except (ValueError, AttributeError):
            date_str = memory.created_at
        
        date_label = ctk.CTkLabel(card, text=f"Created: {date_str}", text_color="gray", font=("Arial", 10))
        date_label.pack(anchor="w", padx=10, pady=2)
        
        # Action buttons
        actions_frame = ctk.CTkFrame(card)
        actions_frame.pack(fill="x", padx=5, pady=5)
        
        view_btn = ctk.CTkButton(
            actions_frame,
            text="View/Edit",
            command=lambda m=memory: self.view_memory_detail(m),
            width=80
        )
        view_btn.pack(side="left", padx=2)
        
        delete_btn = ctk.CTkButton(
            actions_frame,
            text="Delete",
            command=lambda m=memory: self.delete_memory(m),
            width=80,
            fg_color="darkred",
            hover_color="red"
        )
        delete_btn.pack(side="right", padx=2)
    
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
            title="Confirm Delete"
        )
        result = dialog.get_input()
        
        if result == "DELETE":
            self.db_manager.delete_memory(memory.id)
            self.refresh_memories()
    
    def create_memory(self):
        """Manually create a new memory."""
        if not self.current_session_id:
            return
        
        # Create a blank memory
        memory = self.db_manager.create_memory(
            session_id=self.current_session_id,
            kind="semantic",
            content="New memory - click to edit",
            priority=3,
            tags=[]
        )
        
        self.refresh_memories()
        self.view_memory_detail(memory)
    
    def export_memories(self):
        """Export memories to a JSON file."""
        if not self.current_session_id:
            return
        
        import json
        from tkinter import filedialog
        
        memories = self.db_manager.get_memories_by_session(self.current_session_id)
        
        export_data = []
        for mem in memories:
            export_data.append({
                "kind": mem.kind,
                "content": mem.content,
                "priority": mem.priority,
                "tags": mem.tags_list(),
                "created_at": mem.created_at
            })
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    def import_memories(self):
        """Import memories from a JSON file."""
        if not self.current_session_id:
            return
        
        import json
        from tkinter import filedialog
        
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            for mem_data in import_data:
                self.db_manager.create_memory(
                    session_id=self.current_session_id,
                    kind=mem_data.get("kind", "semantic"),
                    content=mem_data.get("content", ""),
                    priority=mem_data.get("priority", 3),
                    tags=mem_data.get("tags", [])
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
            title="Confirm Clear All"
        )
        result = dialog.get_input()
        
        if result == "DELETE ALL":
            memories = self.db_manager.get_memories_by_session(self.current_session_id)
            for mem in memories:
                self.db_manager.delete_memory(mem.id)
            self.refresh_memories()


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
            kind_frame,
            values=["episodic", "semantic", "lore", "user_pref"]
        )
        self.kind_menu.pack(side="left", padx=5)
        
        # Priority slider
        priority_frame = ctk.CTkFrame(self)
        priority_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(priority_frame, text="Priority:").pack(side="left", padx=5)
        self.priority_slider = ctk.CTkSlider(
            priority_frame,
            from_=1,
            to=5,
            number_of_steps=4
        )
        self.priority_slider.pack(side="left", padx=5, fill="x", expand=True)
        
        self.priority_label = ctk.CTkLabel(priority_frame, text="3")
        self.priority_label.pack(side="left", padx=5)
        
        self.priority_slider.configure(command=self._update_priority_label)
        
        # Tags entry
        tags_frame = ctk.CTkFrame(self)
        tags_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(tags_frame, text="Tags (comma-separated):").pack(anchor="w", padx=5)
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
        
        self.meta_label = ctk.CTkLabel(meta_frame, text="", text_color="gray", font=("Arial", 10))
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
        self.db_manager.update_memory(
            self.memory.id,
            kind=new_kind,
            content=new_content,
            priority=new_priority,
            tags=new_tags
        )
        
        if self.on_save_callback:
            self.on_save_callback()
        
        self.destroy()