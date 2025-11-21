"""
Manages chat bubble rendering and display.

New responsibilities:
- Manage chat bubble lifecycle
- Handle dynamic width calculations
- Auto-scroll management
- Clean up destroyed widgets
- Support rich text and location cards
"""

import math
import re
import tkinter
from typing import List

import customtkinter as ctk

from app.gui.styles import Theme, get_chat_bubble_style, get_location_card_style


class ChatBubbleManager:
    """
    Manages the chat history display with dynamic bubble sizing.
    """

    def __init__(self, chat_frame: ctk.CTkScrollableFrame, window: ctk.CTk):
        """
        Initialize the chat bubble manager.

        Args:
            chat_frame: Scrollable frame to display chat bubbles in
            window: Main window reference for resize events
        """
        self.chat_frame = chat_frame
        self.window = window

        # Track bubble content labels for resize updates
        self.bubble_labels: List[ctk.CTkTextbox] = []
        self._last_chat_width = 0  # Track width changes

        # Setup resize handler
        self.setup_resize_handler()

    def setup_resize_handler(self):
        """
        Bind window resize event to update bubble widths.
        """
        self.window.bind("<Configure>", self._on_window_resize)

    def add_message(self, role: str, content: str):
        """
        Add a message as a chat bubble.

        Args:
            role: Message role ("user", "assistant", "system", "thought")
            content: Message content text
        """
        style = get_chat_bubble_style(role)

        # Bubble container
        bubble_container = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        bubble_container.pack(
            fill="x", padx=Theme.spacing.padding_md, pady=Theme.spacing.bubble_margin
        )

        # Bubble frame with styling
        bubble_kwargs = {
            "fg_color": style["fg_color"],
            "corner_radius": style["corner_radius"],
        }
        if "border_width" in style:
            bubble_kwargs["border_width"] = style["border_width"]
            bubble_kwargs["border_color"] = style["border_color"]

        bubble = ctk.CTkFrame(bubble_container, **bubble_kwargs)
        bubble.pack(anchor=style["anchor"], padx=Theme.spacing.padding_sm)

        # Role label
        role_label = ctk.CTkLabel(
            bubble,
            text=style["label"],
            font=Theme.fonts.body_small
            if role != "thought"
            else Theme.fonts.body_italic,
            text_color=style["text_color"],
        )
        role_label.pack(
            anchor="w",
            padx=Theme.spacing.bubble_padding_x,
            pady=(Theme.spacing.bubble_padding_y_top, 0),
        )

        # Calculate dynamic width
        bubble_width = self._calculate_bubble_width()

        # RICH TEXT SUPPORT: Use CTkTextbox instead of Label

        # Estimate characters per line based on pixel width (avg char width ~10px for Arial 18)
        chars_per_line = max(1, bubble_width // 10)

        # Calculate wrapping lines based on content length
        wrapped_lines = math.ceil(len(content) / chars_per_line)

        # Add explicit newlines from the text
        newline_count = content.count("\n")

        # Total lines approximation
        total_lines = wrapped_lines + newline_count

        # Calculate pixel height: ~28px per line for 18pt font + 20px padding
        # Clamp between 40 (min) and 800 (max) to prevent layout glitches
        height = min(max((total_lines * 28) + 20, 40), 800)

        content_box = ctk.CTkTextbox(
            bubble,
            height=height,
            width=bubble_width,
            font=Theme.fonts.body if role != "thought" else Theme.fonts.body_italic,
            text_color=style["text_color"],
            fg_color="transparent",
            wrap="word",
            activate_scrollbars=False,
        )
        content_box.pack(
            anchor="w",
            padx=15,
            pady=(Theme.spacing.padding_xs, Theme.spacing.bubble_padding_y_bottom),
        )

        # Insert text and parse markdown-style **Entities**
        self._insert_rich_text(content_box, content)
        content_box.configure(state="disabled")  # Read-only

        # Store reference to the label for resize updates
        self.bubble_labels.append(content_box)

        # Auto-scroll to bottom
        self._scroll_to_bottom()

    def _insert_rich_text(self, textbox, content):
        """Parses **Name** syntax and applies formatting tags."""
        # Reset
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")

        # Correct regex for **text**
        parts = re.split(r"(\*\*.*?\*\*)", content)

        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                # It's an entity
                text = part[2:-2]  # Strip the **
                textbox.insert("end", text, "entity")
            else:
                textbox.insert("end", part)

        # Configure tag style (Gold color for entities)
        # Note: CTkTextbox passes tags to underlying tk.Text
        textbox._textbox.tag_config(
            "entity", foreground=Theme.colors.text_gold, font=Theme.fonts.heading
        )
        textbox.configure(state="disabled")

    def add_location_card(self, location_data: dict):
        """Renders a visual card for a location change."""
        style = get_location_card_style()

        container = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        container.pack(fill="x", padx=Theme.spacing.padding_lg, pady=15)

        card = ctk.CTkFrame(container, **style)
        card.pack(fill="x", expand=True)

        # Header
        name = location_data.get("name", "Unknown Location")
        ctk.CTkLabel(
            card,
            text=f"📍 {name}",
            font=("Arial", 24, "bold"),
            text_color=Theme.colors.text_gold,
        ).pack(anchor="w", padx=20, pady=(15, 5))

        # Visual Description (Italic)
        desc = location_data.get("description_visual", "No visual description.")
        ctk.CTkLabel(
            card,
            text=desc,
            font=("Arial", 14, "italic"),
            text_color=Theme.colors.text_secondary,
            wraplength=500,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 15))

        self._scroll_to_bottom()

    def clear_history(self):
        """
        Clear all chat bubbles.
        """
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
        self.bubble_labels.clear()

    def _calculate_bubble_width(self) -> int:
        """
        Calculate the appropriate bubble width based on chat frame width.
        """
        frame_width = self.chat_frame.winfo_width()
        if frame_width <= 1:
            frame_width = Theme.dimensions.window_width * 0.75
        usable_width = frame_width - 30
        bubble_width = int(usable_width * Theme.spacing.bubble_width_percent)
        bubble_width = max(bubble_width, Theme.spacing.bubble_min_width)
        return bubble_width

    def _on_window_resize(self, event):
        """Update all bubble widths when the window is resized."""
        current_width = self.window.winfo_width()

        if abs(current_width - self._last_chat_width) > 50:
            self._last_chat_width = current_width
            new_width = self._calculate_bubble_width()

            active_labels = []
            for label in self.bubble_labels:
                try:
                    if label.winfo_exists():
                        label.configure(
                            width=new_width
                        )  # Textbox uses width, not wraplength
                        active_labels.append(label)
                except (tkinter.TclError, AttributeError, RuntimeError):
                    pass
            self.bubble_labels = active_labels

    def _scroll_to_bottom(self):
        """
        Scroll the chat to the bottom.
        """
        self.window.after_idle(lambda: self.chat_frame._parent_canvas.yview_moveto(1.0))
