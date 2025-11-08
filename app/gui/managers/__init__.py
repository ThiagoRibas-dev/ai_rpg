"""
GUI Manager classes for separating concerns.

Created: Part of main_view.py refactoring
Purpose: Modularize MainView into focused manager components

Each manager handles a specific domain:
- ChatBubbleManager: Chat display and resizing
- ToolVisualizationManager: Tool call/result display
- UIQueueHandler: UI queue processing and routing
- SessionManager: Session CRUD and selection
- PromptManager: Prompt CRUD and selection
- InspectorManager: Inspector view coordination
"""

from app.gui.managers.chat_bubble_manager import ChatBubbleManager
from app.gui.managers.tool_visualization_manager import ToolVisualizationManager
from app.gui.managers.ui_queue_handler import UIQueueHandler
from app.gui.managers.session_manager import SessionManager
from app.gui.managers.prompt_manager import PromptManager
from app.gui.managers.inspector_manager import InspectorManager
from app.gui.managers.history_manager import HistoryManager

__all__ = [
    "ChatBubbleManager",
    "ToolVisualizationManager",
    "UIQueueHandler",
    "SessionManager",
    "PromptManager",
    "InspectorManager",
    "HistoryManager",
]
