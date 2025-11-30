import logging
import customtkinter as ctk
from app.gui.styles import Theme

logger = logging.getLogger(__name__)


def render_widget(parent, label, value, widget_type, max_val=None):
    """Generic renderer for stat widgets."""
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", padx=5, pady=2)

    # Label
    ctk.CTkLabel(
        frame, text=label, width=120, anchor="w", font=Theme.fonts.body_small
    ).pack(side="left")

    # Widget Logic
    if widget_type == "bar" and max_val is not None:
        # Progress Bar Layout
        try:
            pct = (
                max(0.0, min(1.0, float(value) / float(max_val)))
                if max_val and float(max_val) > 0
                else 0
            )
        except (ValueError, TypeError, ZeroDivisionError):
            pct = 0

        # Clear frame to handle layout specifically for bar
        for widget in frame.winfo_children():
            widget.destroy()

        # Top Row: Label ... Val/Max
        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=label, font=Theme.fonts.body_small).pack(side="left")
        ctk.CTkLabel(top, text=f"{value}/{max_val}", font=Theme.fonts.body_small).pack(
            side="right"
        )

        bar = ctk.CTkProgressBar(frame, height=10)
        bar.pack(fill="x", pady=(2, 5))
        bar.set(pct)

        # Color coding
        if "hp" in label.lower():
            bar.configure(progress_color="#c0392b")  # Red
        elif "mana" in label.lower() or "mp" in label.lower():
            bar.configure(progress_color="#2980b9")  # Blue

    elif widget_type == "clock":
        # Segmented circle/box representation
        try:
            cur = int(value)
            mx = int(max_val) if max_val else 4
        except Exception as e:
            logger.warning(f"Failed to parse clocks: {e}")
            cur, mx = 0, 4

        dots = "â— " * cur + "â—‹" * max(0, mx - cur)
        ctk.CTkLabel(
            frame, text=dots, text_color=Theme.colors.text_gold, font=("Arial", 16)
        ).pack(side="right", padx=5)

    elif widget_type == "checkbox":
        state = "⛔" if value else "🌟"
        ctk.CTkLabel(frame, text=state, font=("Arial", 16)).pack(side="right", padx=5)

    else:
        # Default: Text/Number/Bonus
        val_str = str(value)
        if widget_type == "bonus" and isinstance(value, (int, float)) and value >= 0:
            val_str = f"+{value}"

        ctk.CTkLabel(
            frame, text=val_str, anchor="e", text_color=Theme.colors.text_secondary
        ).pack(side="right", padx=5, expand=True, fill="x")


def display_message_state(parent, message, is_error=False):
    for widget in parent.winfo_children():
        widget.destroy()
    color = Theme.colors.tool_error if is_error else Theme.colors.text_muted
    ctk.CTkLabel(
        parent, text=message, text_color=color, font=Theme.fonts.body, wraplength=400
    ).pack(expand=True, pady=20)


def create_quest_card(parent: ctk.CTkFrame, quest_id: str, quest: dict):
    """Creates a card widget for a single quest."""
    card = ctk.CTkFrame(parent, border_width=2)
    card.pack(fill="x", padx=5, pady=5)

    title = quest.get("title", "Unknown Quest")
    quest_type = quest.get("type", "side")
    status = quest.get("status", "active")

    icon = "✨" if quest_type == "main" else "🎐"
    status_color = (
        Theme.colors.text_tool_success
        if status == "completed"
        else Theme.colors.text_secondary
    )

    header = ctk.CTkLabel(
        card,
        text=f"{icon} {title} [{status.upper()}]",
        font=Theme.fonts.subheading,
        anchor="w",
        text_color=status_color,
    )
    header.pack(fill="x", padx=10, pady=(10, 5))

    progress = quest.get("progress")
    if progress:
        ctk.CTkLabel(
            card, text=f"Progress: {progress}", anchor="w", font=Theme.fonts.body_small
        ).pack(fill="x", padx=10, pady=2)


def create_memory_card(parent: ctk.CTkFrame, memory, callbacks: dict):
    """Creates a visual card for a single memory."""
    # This function was in the previous file, ensuring we don't break imports.
    card = ctk.CTkFrame(parent, border_width=2)
    card.pack(fill="x", padx=5, pady=5)
    ctk.CTkLabel(card, text=memory.content[:50] + "...").pack(padx=10, pady=10)
