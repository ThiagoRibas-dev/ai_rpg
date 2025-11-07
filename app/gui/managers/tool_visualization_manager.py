"""
Manages tool call visualization in the dedicated panel.

MIGRATION SOURCE: main_view.py lines 451-500
Extracted methods:
- add_tool_call() (lines 451-480)
- add_tool_result() (lines 481-500)

New responsibilities:
- Display tool calls with arguments
- Display tool results (success/error)
- Auto-scroll tool panel
"""

import customtkinter as ctk
from app.gui.styles import Theme, get_tool_call_style


class ToolVisualizationManager:
    """
    Manages the tool calls visualization panel.
    
    MIGRATION NOTES:
    - Extracted from: MainView (tool visualization methods lines 451-500)
    - No state management (stateless display only)
    """
    
    def __init__(self, tool_calls_frame: ctk.CTkScrollableFrame):
        """
        Initialize the tool visualization manager.
        
        MIGRATION NOTES:
        - tool_calls_frame: Previously self.tool_calls_frame
        - Created by InspectorManager, passed to this manager
        
        Args:
            tool_calls_frame: Scrollable frame for displaying tool calls
        """
        self.tool_calls_frame = tool_calls_frame
    
    def add_tool_call(self, tool_name: str, args: dict):
        """
        Add a tool call to the dedicated tool calls panel.
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"🔧 ToolVisualizationManager.add_tool_call: {tool_name}")
        
        style = get_tool_call_style()
        
        # Create tool call card
        call_frame = ctk.CTkFrame(
            self.tool_calls_frame, 
            fg_color=style["fg_color"], 
            corner_radius=style["corner_radius"]
        )
        call_frame.pack(fill="x", padx=style["padding"], pady=style["margin"])
        
        # Header with tool name
        header = ctk.CTkLabel(
            call_frame,
            text=f"🛠️ {tool_name}",
            font=Theme.fonts.subheading,
            text_color=style["header_color"]
        )
        header.pack(anchor="w", padx=Theme.spacing.padding_md, 
                pady=(Theme.spacing.padding_sm, Theme.spacing.padding_xs))
        
        # Arguments (truncated if too long)
        args_text = str(args)
        if len(args_text) > 100:
            args_text = args_text[:100] + "..."
        
        args_label = ctk.CTkLabel(
            call_frame,
            text=f"Args: {args_text}",
            font=Theme.fonts.monospace,
            text_color=style["text_color"],
            wraplength=Theme.dimensions.wrap_tool,
            justify="left"
        )
        args_label.pack(anchor="w", padx=Theme.spacing.padding_md, 
                    pady=(0, Theme.spacing.padding_sm))
        
        logger.debug("✅ Tool call card created and packed")
        
        # Auto-scroll tool calls panel
        try:
            self.tool_calls_frame.after_idle(
                lambda: self.tool_calls_frame._parent_canvas.yview_moveto(1.0)
            )
            logger.debug("🔽 Scrolled to bottom")
        except Exception as e:
            logger.warning(f"Auto-scroll failed: {e}")
    
    def add_tool_result(self, result: any, is_error: bool = False):
        """
        Add a tool result to the most recent tool call card.
        
        Args:
            result: Tool execution result
            is_error: Whether this is an error result
        """
        children = self.tool_calls_frame.winfo_children()
        if not children:
            return
        
        last_frame = children[-1]
        style = get_tool_call_style()
        
        # Truncate long results
        result_text = str(result)
        if len(result_text) > 200:
            result_text = result_text[:200] + "..."
        
        # Color based on success/error
        color = style["error_color"] if is_error else style["success_color"]
        icon = "❌" if is_error else "✅"
        
        # Result label
        result_label = ctk.CTkLabel(
            last_frame,
            text=f"{icon} Result: {result_text}",
            font=Theme.fonts.monospace,
            text_color=color,
            wraplength=Theme.dimensions.wrap_tool,
            justify="left"
        )
        result_label.pack(anchor="w", padx=Theme.spacing.padding_md, 
                         pady=(0, Theme.spacing.padding_sm))
        
        # Auto-scroll tool calls panel
        self.tool_calls_frame.after_idle(
            lambda: self.tool_calls_frame._parent_canvas.yview_moveto(1.0)
        )
