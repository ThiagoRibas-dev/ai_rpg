"""
Manages chat bubble rendering and display.

New responsibilities:
- Manage chat bubble lifecycle
- Handle dynamic width calculations
- Auto-scroll management
- Clean up destroyed widgets
"""

import tkinter
import customtkinter as ctk
from typing import List
from app.gui.styles import Theme, get_chat_bubble_style


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
        self.bubble_labels: List[ctk.CTkLabel] = []
        self._last_chat_width = 0  # Track width changes
        
        # Setup resize handler
        self.setup_resize_handler()
    
    def setup_resize_handler(self):
        """
        Bind window resize event to update bubble widths.
        """
        self.window.bind("&lt;Configure&gt;", self._on_window_resize)
    
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
        bubble_container.pack(fill="x", padx=Theme.spacing.padding_md, pady=Theme.spacing.bubble_margin)
        
        # Bubble frame with styling
        bubble_kwargs = {
            "fg_color": style["fg_color"],
            "corner_radius": style["corner_radius"]
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
            font=Theme.fonts.body_small if role != "thought" else Theme.fonts.body_italic,
            text_color=style["text_color"]
        )
        role_label.pack(anchor="w", padx=Theme.spacing.bubble_padding_x, 
                       pady=(Theme.spacing.bubble_padding_y_top, 0))
        
        # Calculate dynamic width
        bubble_width = self._calculate_bubble_width()
        
        # Content label with wrapping
        content_label = ctk.CTkLabel(
            bubble,
            text=content,
            font=Theme.fonts.body if role != "thought" else Theme.fonts.body_italic,
            text_color=style["text_color"],
            wraplength=bubble_width,
            justify="left"
        )
        content_label.pack(anchor="w", padx=Theme.spacing.padding_md, 
                          pady=(Theme.spacing.padding_xs, Theme.spacing.bubble_padding_y_bottom))
        
        # Store reference to the label for resize updates
        self.bubble_labels.append(content_label)
        
        # Auto-scroll to bottom
        self._scroll_to_bottom()
    
    def clear_history(self):
        """
        Clear all chat bubbles.
        """
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
        # ✅ FIX: Clear the bubble_labels list immediately
        self.bubble_labels.clear()
    
    def _calculate_bubble_width(self) -> int:
        """
        Calculate the appropriate bubble width based on chat frame width.
        - No logic changes
        
        Returns:
            Calculated bubble width in pixels
        """
        # Get the actual width of the chat frame
        frame_width = self.chat_frame.winfo_width()
        
        # If window hasn't been drawn yet, use a default
        if frame_width <= 1:
            frame_width = Theme.dimensions.window_width * 0.75
        
        # Subtract scrollbar width and padding
        usable_width = frame_width - 30
        
        # Calculate percentage-based width
        bubble_width = int(usable_width * Theme.spacing.bubble_width_percent)
        
        # Ensure minimum width
        bubble_width = max(bubble_width, Theme.spacing.bubble_min_width)
        
        return bubble_width
    
    def _on_window_resize(self, event):
        """
        Update all bubble widths when the window is resized.
        
        Args:
            event: Tkinter resize event
        """
        # Only update if the window width actually changed significantly
        current_width = self.window.winfo_width()
        
        if abs(current_width - self._last_chat_width) > 50:  # 50+ pixels change threshold
            self._last_chat_width = current_width
            new_width = self._calculate_bubble_width()
            
            # ✅ FIX: Clean up destroyed widgets while updating
            active_labels = []
            for label in self.bubble_labels:
                try:
                    if label.winfo_exists():
                        label.configure(wraplength=new_width)
                        active_labels.append(label)  # Keep only active widgets
                except (tkinter.TclError, AttributeError, RuntimeError):
                    # Widget is destroyed or invalid - skip it
                    pass
            
            # ✅ FIX: Replace list with only active widgets
            self.bubble_labels = active_labels
    
    def _scroll_to_bottom(self):
        """
        Scroll the chat to the bottom.
        """
        # Use after_idle to ensure the frame is updated before scrolling
        self.window.after_idle(lambda: self.chat_frame._parent_canvas.yview_moveto(1.0))
