"""
UI builder classes for constructing widget hierarchies.

Created: Part of main_view.py refactoring
Purpose: Separate widget construction from business logic
"""

from app.gui.builders.main_panel_builder import MainPanelBuilder
from app.gui.builders.control_panel_builder import ControlPanelBuilder

__all__ = [
    'MainPanelBuilder',
    'ControlPanelBuilder',
]
