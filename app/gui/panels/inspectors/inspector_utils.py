# File: app/gui/panels/inspectors/inspector_utils.py

import logging
import customtkinter as ctk
from app.gui.styles import Theme

logger = logging.getLogger(__name__)


def render_widget(parent, label, value, widget_type, meta=None):
    """
    Generic renderer for stat widgets.

    Args:
        parent: The parent CTk frame.
        label: The label text for the stat.
        value: The current value.
        widget_type: String identifier for the widget style (e.g., 'die', 'track', 'bar').
        meta: Optional dict containing extra info like 'max', 'rendering', etc.
    """
    if meta is None:
        meta = {}

    rendering = meta.get("rendering", {})

    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", padx=5, pady=2)

    # Label (Left side)
    ctk.CTkLabel(
        frame, text=label, width=120, anchor="w", font=Theme.fonts.body_small
    ).pack(side="left")

    # --- WIDGET LOGIC ---

    if widget_type == "die":
        # Kids on Bikes / Savage Worlds style badge
        text_val = str(value)

        # Color code based on die size size for visual flair
        bg_color = Theme.colors.bg_tertiary
        if text_val in ["d20", "d12"]:
            bg_color = "#8e44ad"  # Purple
        elif text_val in ["d8", "d10"]:
            bg_color = "#2980b9"  # Blue
        elif text_val in ["d4", "d6"]:
            bg_color = "#7f8c8d"  # Grey

        badge = ctk.CTkLabel(
            frame,
            text=text_val,
            fg_color=bg_color,
            corner_radius=6,
            width=45,
            height=24,
            font=("Arial", 12, "bold"),
        )
        badge.pack(side="right", padx=5)

    elif widget_type == "ladder":
        # Fate style lookup (e.g. 4 -> "Great (+4)")
        lookup = rendering.get("lookup_map", {})
        adj = lookup.get(str(value), "")

        # Format: "Adjective (+Value)"
        display_text = str(value)
        if adj:
            val_int = (
                int(value)
                if str(value).isdigit()
                or (str(value).startswith("-") and str(value)[1:].isdigit())
                else 0
            )
            sign = "+" if val_int > 0 else ""
            display_text = f"{adj} ({sign}{value})"

        ctk.CTkLabel(
            frame,
            text=display_text,
            text_color=Theme.colors.text_gold,
            font=("Arial", 12, "bold"),
        ).pack(side="right", padx=5)

    elif widget_type == "track":
        # Scum & Villainy / Vampire style checkboxes
        # value = current marked boxes (int)
        # meta['max'] = total boxes (length)
        try:
            current = int(value) if value is not None else 0
            total = int(meta.get("max", 5))
        except (ValueError, TypeError):
            current, total = 0, 5

        track_frame = ctk.CTkFrame(frame, fg_color="transparent")
        track_frame.pack(side="right", padx=5)

        for i in range(total):
            is_checked = i < current
            # Visual style: Filled box vs Empty box
            char = "[x]" if is_checked else "[ ]"
            color = Theme.colors.tool_error if is_checked else "gray"

            lbl = ctk.CTkLabel(
                track_frame, text=char, text_color=color, font=("Arial", 14), width=15
            )
            lbl.pack(side="left", padx=1)

    elif widget_type == "bar":
        # Existing Progress Bar logic
        max_val = meta.get("max")

        # Calculate percentage safely
        try:
            pct = 0
            if max_val and float(max_val) > 0:
                pct = max(0.0, min(1.0, float(value) / float(max_val)))
        except (ValueError, TypeError, ZeroDivisionError):
            pct = 0
            max_val = "?"

        # Container for the bar + text
        bar_container = ctk.CTkFrame(frame, fg_color="transparent")
        bar_container.pack(side="right", fill="x", expand=True, padx=5)

        # Text overlay (Value / Max)
        ctk.CTkLabel(
            bar_container,
            text=f"{value}/{max_val}",
            font=Theme.fonts.body_small,
            anchor="e",
        ).pack(side="top", fill="x")

        # The Bar itself
        bar = ctk.CTkProgressBar(bar_container, height=8)
        bar.pack(side="bottom", fill="x", pady=(2, 0))
        bar.set(pct)

        # Color coding hints
        if label and "hp" in label.lower():
            bar.configure(progress_color="#c0392b")  # Red
        elif label and ("mana" in label.lower() or "mp" in label.lower()):
            bar.configure(progress_color="#2980b9")  # Blue

    elif widget_type == "clock":
        # Segmented circle representation (Simulated with chars)
        try:
            cur = int(value)
            mx = int(meta.get("max", 4))
        except (ValueError, TypeError):
            cur, mx = 0, 4

        # Visual: Filled dots vs Empty diamonds
        dots = "•" * cur + "◇" * max(0, mx - cur)
        ctk.CTkLabel(
            frame, text=dots, text_color=Theme.colors.text_gold, font=("Arial", 16)
        ).pack(side="right", padx=5)

    elif widget_type == "checkbox":
        # Boolean state
        state = "✔️" if value else "❌"
        ctk.CTkLabel(frame, text=state, font=("Arial", 16)).pack(side="right", padx=5)

    else:
        # Default: Text/Number/Bonus
        val_str = str(value)
        if widget_type == "bonus":
            try:
                if float(value) >= 0:
                    val_str = f"+{value}"
            except (ValueError, TypeError):
                pass

        ctk.CTkLabel(
            frame, text=val_str, anchor="e", text_color=Theme.colors.text_secondary
        ).pack(side="right", padx=5, expand=True, fill="x")


def display_message_state(parent, message, is_error=False):
    """Helper to show a centered message in a frame (e.g. 'No Session')."""
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

    icon = "🌟" if quest_type == "main" else "⭐"
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
    from app.gui.styles import get_memory_kind_color

    card = ctk.CTkFrame(parent, fg_color=Theme.colors.bg_tertiary)
    card.pack(fill="x", padx=5, pady=5)

    # Top Row: Badge + Priority
    top_row = ctk.CTkFrame(card, fg_color="transparent")
    top_row.pack(fill="x", padx=10, pady=(5, 0))

    # Kind Badge
    kind_color = get_memory_kind_color(memory.kind)
    ctk.CTkLabel(
        top_row,
        text=memory.kind.upper(),
        fg_color=kind_color,
        text_color="white",
        corner_radius=4,
        font=("Arial", 10, "bold"),
    ).pack(side="left")

    # Priority Stars
    stars = "â˜…" * memory.priority
    ctk.CTkLabel(top_row, text=stars, text_color="gold", font=("Arial", 12)).pack(
        side="right"
    )

    # Content
    content_text = memory.content
    if len(content_text) > 150:
        content_text = content_text[:150] + "..."

    ctk.CTkLabel(
        card, text=content_text, wraplength=350, anchor="w", justify="left"
    ).pack(fill="x", padx=10, pady=5)

    # Footer: Tags + Buttons
    footer = ctk.CTkFrame(card, fg_color="transparent")
    footer.pack(fill="x", padx=10, pady=(0, 5))

    # Tags
    tags_str = ", ".join(memory.tags_list()[:3])
    if tags_str:
        ctk.CTkLabel(
            footer, text=f"Tags: {tags_str}", text_color="gray", font=("Arial", 10)
        ).pack(side="left")

    # Buttons
    btn_frame = ctk.CTkFrame(footer, fg_color="transparent")
    btn_frame.pack(side="right")

    ctk.CTkButton(
        btn_frame,
        text="âœ ",
        width=30,
        height=20,
        command=lambda: callbacks["on_view"](memory),
    ).pack(side="left", padx=2)

    ctk.CTkButton(
        btn_frame,
        text="â—fb",
        width=30,
        height=20,
        fg_color="darkred",
        command=lambda: callbacks["on_delete"](memory),
    ).pack(side="left", padx=2)
