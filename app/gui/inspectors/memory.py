from nicegui import ui

from app.gui.dialogs.memory_editor import MemoryEditorDialog
from app.models.vocabulary import MemoryKind


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
        if self.active_tab == "All":
            kind_filter = None
        elif self.active_tab == "Facts":
            kind_filter = MemoryKind.SEMANTIC
        elif self.active_tab == "Preferences":
            kind_filter = MemoryKind.USER_PREF
        elif self.active_tab == "Rules":
            kind_filter = MemoryKind.RULE
        # Episodic, Lore, or any future tab where label == kind title-cased
        # Enums don't have .lower() on the class, only instances, so handle matching text
        elif self.active_tab == "Episodic":
            kind_filter = MemoryKind.EPISODIC
        elif self.active_tab == "Lore":
            kind_filter = MemoryKind.LORE
        else:
            kind_filter = self.active_tab.lower()

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
                ui.label(f"📖 {counts.get(MemoryKind.EPISODIC, 0)}").tooltip("Episodic Events")
                ui.label(f"💡 {counts.get(MemoryKind.SEMANTIC, 0)}").tooltip("Facts / Knowledge")
                ui.label(f"📜 {counts.get(MemoryKind.LORE, 0)}").tooltip("World Lore")
                ui.label(f"⚙️ {counts.get(MemoryKind.USER_PREF, 0)}").tooltip("Preferences")
                ui.label(f"⚖️ {counts.get(MemoryKind.RULE, 0)}").tooltip("System Rules")

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
            # Initialize with current active_tab to avoid spurious refresh
            with (
                ui.tabs(value=self.active_tab)
                .classes("w-full text-xs")
                .on_value_change(self._on_tab_change)
            ):
                ui.tab("All")
                ui.tab("Episodic")
                ui.tab("Facts")  # semantic
                ui.tab("Lore")  # lore
                ui.tab("Preferences")  # user_pref
                ui.tab("Rules")  # rule

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
            MemoryKind.EPISODIC: "blue-900",
            MemoryKind.SEMANTIC: "green-900",
            MemoryKind.LORE: "purple-900",
            MemoryKind.USER_PREF: "orange-900",
            MemoryKind.RULE: "red-900",
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
