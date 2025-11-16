import customtkinter as ctk
import json
from app.gui.styles import Theme


class StateViewerDialog(ctk.CTkToplevel):
    """Debug tool to view raw game state."""

    def __init__(self, parent, db_manager, session_id):
        super().__init__(parent)

        self.db_manager = db_manager
        self.session_id = session_id

        self.title("Game State Viewer")
        self.geometry("800x600")

        # Stats header
        self.stats_label = ctk.CTkLabel(self, text="Loading...", font=Theme.fonts.body)
        self.stats_label.pack(padx=10, pady=10)

        # State display
        self.state_textbox = ctk.CTkTextbox(self, font=Theme.fonts.monospace)
        self.state_textbox.pack(fill="both", expand=True, padx=10, pady=10)

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(button_frame, text="🔄 Refresh", command=self.refresh).pack(
            side="left", expand=True, fill="x", padx=5
        )

        ctk.CTkButton(
            button_frame, text="📋 Copy JSON", command=self.copy_to_clipboard
        ).pack(side="left", expand=True, fill="x", padx=5)

        ctk.CTkButton(
            button_frame,
            text="🗑️ Clear All State",
            command=self.clear_state,
            fg_color=Theme.colors.button_danger,
        ).pack(side="left", expand=True, fill="x", padx=5)

        self.refresh()

    def refresh(self):
        """Load and display current state."""
        try:
            state = self.db_manager.game_state.get_all(self.session_id)
            stats = self.db_manager.game_state.get_statistics(self.session_id)

            # Update stats
            total = stats.get("total_entities", 0)
            by_type = stats.get("by_type", {})
            stats_text = f"Total Entities: {total} | " + " | ".join(
                [f"{k}: {v}" for k, v in by_type.items()]
            )
            self.stats_label.configure(text=stats_text)

            # Format state as JSON
            display_state = {}
            for entity_type, entities in state.items():
                display_state[entity_type] = {}
                for key, entity_data in entities.items():
                    display_state[entity_type][key] = entity_data["data"]

            json_str = json.dumps(display_state, indent=2)

            self.state_textbox.configure(state="normal")
            self.state_textbox.delete("1.0", "end")
            self.state_textbox.insert("1.0", json_str)
            self.state_textbox.configure(state="disabled")

        except Exception as e:
            self.state_textbox.configure(state="normal")
            self.state_textbox.delete("1.0", "end")
            self.state_textbox.insert("1.0", f"Error loading state: {e}")
            self.state_textbox.configure(state="disabled")

    def copy_to_clipboard(self):
        """Copy JSON to clipboard."""
        text = self.state_textbox.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(text)

    def clear_state(self):
        """Clear all state (with confirmation)."""
        dialog = ctk.CTkInputDialog(
            text="Type 'DELETE' to clear all game state:", title="Confirm Clear"
        )
        result = dialog.get_input()

        if result == "DELETE":
            self.db_manager.clear_game_state(self.session_id)
            self.refresh()
