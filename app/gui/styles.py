"""
Centralized style configuration for the AI-RPG GUI.
Modify colors, fonts, spacing, and other style properties here.
"""

from typing import Dict, Any
from dataclasses import dataclass

# ==================== Color Palette ====================

@dataclass
class ColorScheme:
    """Color scheme for the application."""
    # Backgrounds
    bg_primary: str = "#2B2B2B"
    bg_secondary: str = "#1a1a1a"
    bg_tertiary: str = "#3d3d3d"
    
    # Chat bubbles
    bubble_user: str = "#1e3a5f"
    bubble_ai: str = "#2d4a2b"
    bubble_system: str = "#3d3d3d"
    bubble_thought: str = "#4a4a2d"
    bubble_thought_border: str = "#8a8a6d"
    
    # Tool calls
    tool_call_bg: str = "#2d4a2b"
    tool_success: str = "#B6D7A8"
    tool_error: str = "#FFB6C6"
    
    # Memory inspector
    memory_episodic: str = "#3498db"
    memory_semantic: str = "#2ecc71"
    memory_lore: str = "#9b59b6"
    memory_user_pref: str = "#e67e22"
    
    # Text colors
    text_primary: str = "#ffffff"
    text_secondary: str = "#d0d0d0"
    text_tertiary: str = "#cccccc"
    text_muted: str = "gray"
    text_thought: str = "#d4d4aa"
    text_tool_success: str = "#90EE90"
    text_gold: str = "#FFD700"
    
    # Buttons
    button_default: tuple = ("#3a7ebf", "#1f538d")  # (light, dark)
    button_selected: str = "blue"
    button_danger: str = "darkred"
    button_danger_hover: str = "red"
    
    # Collapsible frames
    collapsible_header: tuple = ("gray75", "gray25")
    collapsible_header_hover: tuple = ("gray70", "gray30")
    
    # Borders
    border_light: str = "#4a4a4a"
    border_accent: str = "#8a8a6d"


@dataclass
class Fonts:
    """Font configuration for the application."""
    # Font families
    family_default: str = "Arial"
    family_monospace: str = "Courier"
    
    # Font sizes
    size_small: int = 11
    size_normal: int = 13
    size_medium: int = 15
    size_large: int = 18
    size_title: int = 22
    
    # Font styles (family, size, weight)
    heading: tuple = ("Arial", size_title, "bold")
    subheading: tuple = ("Arial", size_large, "bold")
    body: tuple = ("Arial", size_large, "normal")
    button: tuple = ("Arial", size_medium, "normal")
    body_italic: tuple = ("Arial", size_medium, "italic")
    body_small: tuple = ("Arial", size_normal, "normal")
    monospace: tuple = ("Courier", size_normal, "normal")


@dataclass
class Spacing:
    """Spacing and padding configuration."""
    # Padding
    padding_xs: int = 2
    padding_sm: int = 5
    padding_md: int = 10
    padding_lg: int = 20
    
    # Margins
    margin_xs: int = 2
    margin_sm: int = 3
    margin_md: int = 5
    margin_lg: int = 10
    
    # Component-specific
    bubble_padding_x: int = 20
    bubble_padding_y_top: int = 5
    bubble_padding_y_bottom: int = 8
    bubble_margin: int = 5
    bubble_corner_radius: int = 10
    bubble_width_percent: float = 0.8
    bubble_min_width: int = 300
    
    tool_card_padding: int = 5
    tool_card_margin: int = 3
    tool_card_corner_radius: int = 8
    
    memory_card_padding: int = 5
    memory_card_margin: int = 5
    memory_card_corner_radius: int = 5
    
    # Input/textbox heights
    input_height: int = 100
    textbox_small: int = 80
    textbox_medium: int = 100
    scrollable_frame_height: int = 100


@dataclass
class Dimensions:
    """Window and component dimensions."""
    # Main window
    window_width: int = 1200
    window_height: int = 800
    
    # Component widths
    button_small: int = 60
    button_medium: int = 80
    button_large: int = 120
    
    # Wraplengths for text
    wrap_bubble: int = 600
    wrap_tool: int = 300
    wrap_memory: int = 400


# ==================== Default Theme ====================

class Theme:
    """Main theme configuration - modify this to change the entire app's appearance."""
    colors = ColorScheme()
    fonts = Fonts()
    spacing = Spacing()
    dimensions = Dimensions()


# ==================== Style Helper Functions ====================

def get_chat_bubble_style(role: str) -> Dict[str, Any]:
    """Get style configuration for a chat bubble based on role."""
    if role == "user":
        return {
            "fg_color": Theme.colors.bubble_user,
            "text_color": Theme.colors.text_primary,
            "corner_radius": Theme.spacing.bubble_corner_radius,
            "anchor": "e",
            "label": "You",
        }
    elif role == "assistant":
        return {
            "fg_color": Theme.colors.bubble_ai,
            "text_color": Theme.colors.text_primary,
            "corner_radius": Theme.spacing.bubble_corner_radius,
            "anchor": "w",
            "label": "AI",
        }
    elif role == "thought":
        return {
            "fg_color": Theme.colors.bubble_thought,
            "text_color": Theme.colors.text_thought,
            "corner_radius": Theme.spacing.bubble_corner_radius,
            "border_color": Theme.colors.bubble_thought_border,
            "border_width": 1,
            "anchor": "center",
            "label": "💭 AI Thinking",
        }
    else:  # system
        return {
            "fg_color": Theme.colors.bubble_system,
            "text_color": Theme.colors.text_tertiary,
            "corner_radius": Theme.spacing.bubble_corner_radius,
            "anchor": "w",
            "label": role.capitalize(),
        }


def get_tool_call_style() -> Dict[str, Any]:
    """Get style configuration for tool call cards."""
    return {
        "fg_color": Theme.colors.tool_call_bg,
        "corner_radius": Theme.spacing.tool_card_corner_radius,
        "padding": Theme.spacing.tool_card_padding,
        "margin": Theme.spacing.tool_card_margin,
        "header_color": Theme.colors.text_tool_success,
        "text_color": Theme.colors.text_secondary,
        "success_color": Theme.colors.tool_success,
        "error_color": Theme.colors.tool_error,
    }


def get_memory_kind_color(kind: str) -> str:
    """Get color for a memory kind badge."""
    colors = {
        "episodic": Theme.colors.memory_episodic,
        "semantic": Theme.colors.memory_semantic,
        "lore": Theme.colors.memory_lore,
        "user_pref": Theme.colors.memory_user_pref,
    }
    return colors.get(kind, Theme.colors.bg_tertiary)


def get_button_style(variant: str = "default") -> Dict[str, Any]:
    """Get style configuration for buttons."""
    if variant == "danger":
        return {
            "fg_color": Theme.colors.button_danger,
            "hover_color": Theme.colors.button_danger_hover,
        }
    elif variant == "selected":
        return {
            "fg_color": Theme.colors.button_selected,
        }
    else:  # default
        return {
            "fg_color": Theme.colors.button_default,
        }


# ==================== Alternative Themes ====================

class DarkTheme(Theme):
    """Dark theme variant (default)."""
    pass


class LightTheme(Theme):
    """Light theme variant."""
    colors = ColorScheme(
        # Backgrounds
        bg_primary="#f0f0f0",
        bg_secondary="#ffffff",
        bg_tertiary="#e0e0e0",
        
        # Chat bubbles
        bubble_user="#4a90e2",
        bubble_ai="#52c41a",
        bubble_system="#d9d9d9",
        bubble_thought="#fff4e6",
        bubble_thought_border="#d4af37",
        
        # Tool calls
        tool_call_bg="#e6f7ff",
        tool_success="#52c41a",
        tool_error="#ff4d4f",
        
        # Memory inspector (keep same vibrant colors)
        memory_episodic="#3498db",
        memory_semantic="#2ecc71",
        memory_lore="#9b59b6",
        memory_user_pref="#e67e22",
        
        # Text colors
        text_primary="#000000",
        text_secondary="#262626",
        text_tertiary="#595959",
        text_muted="#8c8c8c",
        text_thought="#8b7355",
        text_tool_success="#237804",
        text_gold="#d4af37",
        
        # Buttons
        button_default=("#69b1ff", "#1890ff"),
        button_selected="#1890ff",
        button_danger="#ff4d4f",
        button_danger_hover="#ff7875",
        
        # Collapsible frames
        collapsible_header=("#d9d9d9", "#bfbfbf"),
        collapsible_header_hover=("#bfbfbf", "#a6a6a6"),
        
        # Borders
        border_light="#d9d9d9",
        border_accent="#d4af37",
    )


# ==================== Active Theme ====================
# Change this to switch themes globally
ACTIVE_THEME = DarkTheme


# ==================== Convenience Functions ====================

def apply_theme(theme_class):
    """Switch the active theme globally."""
    global ACTIVE_THEME
    ACTIVE_THEME = theme_class


def get_theme():
    """Get the currently active theme."""
    return ACTIVE_THEME


# ==================== Export for convenience ====================
__all__ = [
    'Theme',
    'DarkTheme',
    'LightTheme',
    'ACTIVE_THEME',
    'get_chat_bubble_style',
    'get_tool_call_style',
    'get_memory_kind_color',
    'get_button_style',
    'apply_theme',
    'get_theme',
]