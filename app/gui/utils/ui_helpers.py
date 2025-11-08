"""
Utility functions for UI operations.

New responsibilities:
- Stateless utility functions
- No dependencies on MainView
"""

import customtkinter as ctk
from typing import List, Tuple, Callable
from app.gui.styles import Theme


def get_mode_display(game_mode: str) -> Tuple[str, str]:
    """
    Get display text and color for game mode.

    Args:
        game_mode: Current game mode string ("SETUP" or "GAMEPLAY")

    Returns:
        Tuple of (display_text, color)

    Example:
        >>> text, color = get_mode_display("SETUP")
        >>> # Returns: ("📋 SETUP", "#FFD700")
    """
    if game_mode == "SETUP":
        return ("📋 SETUP", Theme.colors.text_gold)  # Gold for setup
    elif game_mode == "GAMEPLAY":
        return (
            "⚔️ GAMEPLAY",
            Theme.colors.text_tool_success,
        )  # Green for active gameplay
    else:
        return (f"❓ {game_mode}", Theme.colors.text_muted)  # Gray for unknown


def create_choice_buttons(
    parent_frame: ctk.CTkFrame,
    choices: List[str],
    on_select_callback: Callable[[str], None],
) -> None:
    """
    Creates action choice buttons in the parent frame.

    Args:
        parent_frame: Frame to place buttons in
        choices: List of choice text strings
        on_select_callback: Function to call when a choice is clicked (receives choice text)

    Example:
        >>> create_choice_buttons(
        ...     frame,
        ...     ["Attack the goblin", "Negotiate", "Run away"],
        ...     lambda choice: print(f"Selected: {choice}")
        ... )
    """
    # Clear existing buttons
    for widget in parent_frame.winfo_children():
        widget.destroy()

    if not choices:
        parent_frame.grid_remove()
        return

    parent_frame.grid()

    # Create numbered choice buttons
    for i, choice in enumerate(choices):
        btn = ctk.CTkButton(
            parent_frame,
            text=f"{i + 1}. {choice}",
            command=lambda c=choice: on_select_callback(c),
        )
        btn.pack(side="left", padx=5, pady=5, expand=True, fill="x")
