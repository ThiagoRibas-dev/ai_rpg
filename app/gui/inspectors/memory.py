from nicegui import ui
from app.gui.dialogs.memory_editor import MemoryEditorDialog


class MemoryInspector:
    def __init__(self, db_manager):
        self.db = db_manager
        self.session_id = None
        self.container = None
        self.search_term = ""
        self.active_tab = "All"

        # Stats Labels
        self.lbl_episodic = None
        self.lbl_semantic = None
        self.lbl_lore = None

    def set_session(self, session_id: int):
        self.session_id = session_id
        self.refresh()

    def refresh(self):
        if not self.container:
            return

        # We clear the container to rebuild the view.
        # Note: This does cause search input to lose focus on refresh.
        self.container.clear()

        if not self.session_id:
            with self.container:
                ui.label("No Session").classes("text-gray-500 italic")
            return

        # 1. Fetch Stats
        stats = self.db.memories.get_statistics(self.session_id)
        counts = stats.get("by_kind", {})

        # 2. Fetch Data (Filtered)
        kind_filter = None if self.active_tab == "All" else self.active_tab.lower()
        if kind_filter == "facts":
            kind_filter = "semantic"  # Alias handle

        memories = self.db.memories.query(
            self.session_id,
            kind=kind_filter,
            query_text=self.search_term if self.search_term else None,
            limit=50,
        )

        with self.container:
            # --- Stats Header ---
            with ui.row().classes(
                "w-full justify-between px-2 py-1 bg-slate-900 rounded mb-2 text-xs"
            ):
                ui.label(f"📖 {counts.get('episodic', 0)}").tooltip("Episodic Events")
                ui.label(f"💡 {counts.get('semantic', 0)}").tooltip("Facts/Knowledge")
                ui.label(f"📜 {counts.get('lore', 0)}").tooltip("World Lore")
                ui.label(f"⚙️ {counts.get('user_pref', 0)}").tooltip("Preferences")

            # --- Controls ---
            # Search Input
            ui.input(
                placeholder="Search...",
                value=self.search_term,
                on_change=self._on_search,
            ).props("outlined dense rounded debounce=300").classes(
                "w-full mb-2 bg-slate-800 text-white text-sm"
            )

            # Tabs
            # Fix: Initialize with value to avoid triggering on_change immediately
            with (
                ui.tabs(value=self.active_tab)
                .classes("w-full text-xs")
                .on_value_change(self._on_tab_change)
            ):
                ui.tab("All")
                ui.tab("Episodic")
                ui.tab("Facts")
                ui.tab("Lore")

            # --- List ---
            with ui.scroll_area().classes("h-[500px] w-full pr-2"):
                if not memories:
                    ui.label("No memories found.").classes(
                        "text-gray-500 text-sm italic p-2"
                    )

                for mem in memories:
                    self._render_memory_card(mem)

    def _on_search(self, e):
        # Only refresh if value actually changed
        if self.search_term != e.value:
            self.search_term = e.value
            self.refresh()

    def _on_tab_change(self, e):
        # Only refresh if value actually changed
        if self.active_tab != e.value:
            self.active_tab = e.value
            self.refresh()

    def _render_memory_card(self, mem):
        kind_colors = {
            "episodic": "blue-900",
            "semantic": "green-900",
            "lore": "purple-900",
            "user_pref": "orange-900",
        }
        bg = kind_colors.get(mem.kind, "slate-800")

        # Clickable Card
        with (
            ui.card()
            .classes(
                "w-full bg-slate-800 p-2 mb-2 border border-slate-700 cursor-pointer hover:border-gray-500 group"
            )
            .on("click", lambda: self.edit_memory(mem))
        ):
            with ui.row().classes("w-full justify-between items-center mb-1"):
                ui.badge(mem.kind.upper(), color=bg).classes("text-[10px]")
                with ui.row().classes("gap-1"):
                    ui.label("★" * mem.priority).classes("text-yellow-500 text-xs")
                    # Delete button (hidden until hover)
                    ui.button(
                        icon="delete", on_click=lambda m=mem: self.delete_memory(m)
                    ).props("flat dense round size=xs color=red").classes(
                        "opacity-0 group-hover:opacity-100 transition-opacity"
                    )

            ui.markdown(mem.content).classes("text-sm text-gray-300 leading-tight")

            if mem.tags_list():
                with ui.row().classes("gap-1 mt-2 flex-wrap"):
                    for tag in mem.tags_list():
                        ui.label(f"#{tag}").classes(
                            "text-[10px] text-gray-500 bg-slate-900 px-1 rounded"
                        )

    def edit_memory(self, memory):
        dialog = MemoryEditorDialog(self.db, memory, on_change=self.refresh)
        dialog.open()

    def delete_memory(self, memory):
        self.db.memories.delete(memory.id)
        ui.notify("Memory deleted")
        self.refresh()
