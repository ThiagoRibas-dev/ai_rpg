"""
Manages chat bubble rendering and display.
"""

import tkinter
import customtkinter as ctk
from typing import List
from app.gui.styles import Theme, get_chat_bubble_style, get_location_card_style, get_dice_card_style
import re


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
        
        # --- MODIFIED: Use Serif font for Assistant (Narrative) ---
        # This creates a subconscious separation between "Game" and "Story"
        font_to_use = Theme.fonts.narrative if role == "assistant" else Theme.fonts.body
        if role == "thought":
            font_to_use = Theme.fonts.body_italic

        # --- FIX: Virtual Label Measurement ---
        # We create a dummy label to calculate exactly how tall the text will be when wrapped.
        dummy_label = ctk.CTkLabel(
            self.window, 
            text=content, 
            font=font_to_use,
            wraplength=bubble_width, # Force it to wrap exactly where the textbox would
            anchor="w",
            justify="left"
        )
        
        # Force Tcl/Tk to calculate geometry without rendering to screen
        dummy_label.update() 
        
        req_height = dummy_label.winfo_reqheight()
        dummy_label.destroy() # Cleanup

        # Add padding: Textboxes have internal margins (approx 10px top/bottom) 
        # that Labels don't have.
        textbox_height = req_height + 40
        
        # Clamp height (Min 40, Max 800 before scrolling)
        final_height = min(max(textbox_height, 40), 1200)
        # --------------------------------------

        content_box = ctk.CTkTextbox(
            bubble,
            height=final_height,
            width=bubble_width,
            font=font_to_use,
            text_color=style["text_color"],
            fg_color="transparent",
            wrap="word",
            activate_scrollbars=False
        )
        content_box.pack(
            anchor="w",
            padx=15,
            pady=(Theme.spacing.padding_xs, Theme.spacing.bubble_padding_y_bottom),
        )
        
        # Insert text and parse markdown-style **Entities**
        self._insert_rich_text(content_box, content)
        content_box.configure(state="disabled") # Read-only

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
        parts = re.split(r'(\*\*.*?\*\*)', content)

        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                # It's an entity
                text = part[2:-2]  # Strip the **
                textbox.insert("end", text, "entity")
            else:
                textbox.insert("end", part)

        # Configure tag style (Gold color for entities)
        textbox._textbox.tag_config("entity", foreground=Theme.colors.text_gold, font=Theme.fonts.body_italic)
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
            font=("Arial", 14, "bold"),
            text_color=Theme.colors.text_gold
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        # Visual Description (Italic)
        desc = location_data.get("description_visual", "No visual description.")
        ctk.CTkLabel(
            card,
            text=desc,
            font=("Arial", 14, "italic"),
            text_color=Theme.colors.text_secondary,
            wraplength=500,
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 15))
        
        self._scroll_to_bottom()

    # --- NEW METHOD: Visual Dice Card ---
    def add_dice_card(self, roll_data: dict):
        """
        Renders a visual card for a dice roll event.
        Expected roll_data: {'total': 18, 'rolls': [15], 'modifier': 3, 'spec': '1d20+3'}
        """
        # Determine if it's a "good" roll (simple heuristic for visuals)
        # In a real system, we'd pass 'success': True/False from the backend
        total = roll_data.get("total", 0)
        is_crit = total >= 20
        is_fail = total == 1
        
        style = get_dice_card_style(is_success=not is_fail)
        
        container = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        container.pack(fill="x", padx=Theme.spacing.padding_lg, pady=10)
        
        # The Card
        card = ctk.CTkFrame(
            container, 
            fg_color=style["fg_color"], 
            border_color=style["border_color"] if (is_crit or is_fail) else "gray40", 
            border_width=2 if (is_crit or is_fail) else 1,
            corner_radius=8
        )
        card.pack(anchor="center") # Center the dice roll like a notification

        # Top Row: The Total
        total_label = ctk.CTkLabel(
            card, 
            text=str(total),
            font=("Arial", 24, "bold"),
            text_color=style["accent_color"] if is_crit else "#ffffff"
        )
        total_label.pack(pady=(10, 0), padx=20)

        # Middle Row: The Formula (e.g. "1d20 (15) + 3")
        rolls = roll_data.get("rolls", [])
        mod = roll_data.get("modifier", 0)
        
        rolls_str = str(rolls[0]) if len(rolls) == 1 else str(rolls)
        mod_str = f"+ {mod}" if mod > 0 else (f"- {abs(mod)}" if mod < 0 else "")
        
        formula_text = f"Rolled {rolls_str} {mod_str}"
        
        detail_label = ctk.CTkLabel(
            card,
            text=formula_text,
            font=("Arial", 12),
            text_color="gray80"
        )
        detail_label.pack(pady=(0, 10), padx=20)
        
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
                        label.configure(width=new_width) # Textbox uses width, not wraplength
                        active_labels.append(label)
                except (tkinter.TclError, AttributeError, RuntimeError):
                    pass
            self.bubble_labels = active_labels

    def _scroll_to_bottom(self):
        """
        Scroll the chat to the bottom.
        """
        self.window.after_idle(lambda: self.chat_frame._parent_canvas.yview_moveto(1.0))