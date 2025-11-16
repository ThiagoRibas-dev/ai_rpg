# File: app/gui/panels/inspectors/inspector_utils.py

import customtkinter as ctk
from app.gui.styles import Theme
from datetime import datetime

def create_key_value_row(parent: ctk.CTkFrame, key: str, value: str):
    """Adds a standardized key-value pair display to a parent frame."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=10, pady=2)

    ctk.CTkLabel(row, text=f"{key}:", anchor="w", width=150).pack(side="left")
    ctk.CTkLabel(
        row, text=value, anchor="w", text_color=Theme.colors.text_secondary
    ).pack(side="left", expand=True, fill="x")

def display_message_state(parent: ctk.CTkFrame, message: str, is_error: bool = False):
    """Clears the parent frame and displays a centered message (for empty or error states)."""
    for widget in parent.winfo_children():
        widget.destroy()

    color = Theme.colors.tool_error if is_error else Theme.colors.text_muted
    label = ctk.CTkLabel(
        parent,
        text=message,
        text_color=color,
        font=Theme.fonts.body,
        wraplength=400,
    )
    label.pack(expand=True, pady=50)

def create_quest_card(parent: ctk.CTkFrame, quest_id: str, quest: dict):
    """Creates a card widget for a single quest."""
    card = ctk.CTkFrame(parent, border_width=2)
    card.pack(fill="x", padx=5, pady=5)

    title = quest.get("title", "Unknown Quest")
    quest_type = quest.get("type", "side")
    status = quest.get("status", "active")

    icon = "⭐" if quest_type == "main" else "📜"
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
            card,
            text=f"Progress: {progress}",
            anchor="w",
            font=Theme.fonts.body_small,
        ).pack(fill="x", padx=10, pady=2)

    objectives = quest.get("objectives", [])
    if objectives:
        obj_frame = ctk.CTkFrame(card, fg_color="transparent")
        obj_frame.pack(fill="x", padx=10, pady=5)
        for obj in objectives:
            completed = obj.get("completed", False)
            text = obj.get("text", "")
            checkbox = "✅" if completed else "⬜"
            ctk.CTkLabel(
                obj_frame,
                text=f"{checkbox} {text}",
                anchor="w",
                font=Theme.fonts.body_small,
            ).pack(fill="x", padx=5, pady=1)

def create_memory_card(parent: ctk.CTkFrame, memory, callbacks: dict):
    """Creates a visual card for a single memory."""
    card = ctk.CTkFrame(parent, border_width=2)
    card.pack(fill="x", padx=5, pady=5)

    header = ctk.CTkFrame(card)
    header.pack(fill="x", padx=5, pady=5)

    kind_colors = {
        "episodic": "#3498db",
        "semantic": "#2ecc71",
        "lore": "#9b59b6",
        "user_pref": "#e67e22",
    }
    kind_badge = ctk.CTkLabel(
        header,
        text=memory.kind.upper(),
        fg_color=kind_colors.get(memory.kind, "gray"),
        corner_radius=5,
        width=80,
    )
    kind_badge.pack(side="left", padx=2)

    priority_str = "★" * memory.priority + "☆" * (5 - memory.priority)
    priority_label = ctk.CTkLabel(header, text=priority_str)
    priority_label.pack(side="left", padx=5)

    id_label = ctk.CTkLabel(header, text=f"ID: {memory.id}", text_color="gray")
    id_label.pack(side="right", padx=5)

    access_label = ctk.CTkLabel(
        header, text=f"↺ {memory.access_count}", text_color="gray"
    )
    access_label.pack(side="right", padx=5)

    content_preview = memory.content[:150] + (
        "..." if len(memory.content) > 150 else ""
    )
    content_label = ctk.CTkLabel(
        card, text=content_preview, wraplength=400, justify="left", anchor="w"
    )
    content_label.pack(fill="x", padx=10, pady=5)

    if memory.tags_list():
        tags_frame = ctk.CTkFrame(card)
        tags_frame.pack(fill="x", padx=10, pady=5)
        for tag in memory.tags_list():
            tag_label = ctk.CTkLabel(
                tags_frame, text=f"#{tag}", fg_color="gray30", corner_radius=3
            )
            tag_label.pack(side="left", padx=2)

    try:
        created = datetime.fromisoformat(memory.created_at)
        date_str = created.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        date_str = memory.created_at

    if memory.fictional_time:
        time_display = f"🕐 {memory.fictional_time}"
        fictional_label = ctk.CTkLabel(
            card,
            text=time_display,
            text_color="#FFD700",
            font=("Arial", 11, "bold"),
        )
        fictional_label.pack(anchor="w", padx=10, pady=2)

    date_label = ctk.CTkLabel(
        card, text=f"Real: {date_str}", text_color="gray", font=("Arial", 9)
    )
    date_label.pack(anchor="w", padx=10, pady=2)

    actions_frame = ctk.CTkFrame(card)
    actions_frame.pack(fill="x", padx=5, pady=5)

    if 'on_view' in callbacks:
        view_btn = ctk.CTkButton(
            actions_frame,
            text="View/Edit",
            command=lambda m=memory: callbacks['on_view'](m),
            width=80,
        )
        view_btn.pack(side="left", padx=2)

    if 'on_delete' in callbacks:
        delete_btn = ctk.CTkButton(
            actions_frame,
            text="Delete",
            command=lambda m=memory: callbacks['on_delete'](m),
            width=80,
            fg_color=Theme.colors.button_danger,
            hover_color=Theme.colors.button_danger_hover,
        )
        delete_btn.pack(side="right", padx=2)
