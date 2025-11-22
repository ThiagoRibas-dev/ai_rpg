"""
Builds the control (right) panel of the application.
Contains: Prompt Management, Game Sessions, Advanced Context.
"""

import customtkinter as ctk
from typing import Dict, Any, Callable, Optional
from app.gui.collapsible_frame import CollapsibleFrame
from app.gui.styles import Theme


class ControlPanelBuilder:
    """
    Static factory for building the control (right) panel.
    """

    @staticmethod
    def build(
        parent: ctk.CTk,
        prompt_callbacks: Optional[Dict[str, Callable]],
        session_callback: Optional[Callable],
        save_context_callback: Callable,
    ) -> Dict[str, Any]:
        """
        Build the control panel (Column 2).
        """
        # === Control Panel (Scrollable) ===
        control_panel = ctk.CTkScrollableFrame(parent, fg_color=Theme.colors.bg_primary)
        control_panel.grid(
            row=0,
            column=2,  # CHANGED: Now Column 2
            sticky="nsew",
            padx=(0, Theme.spacing.padding_md),
            pady=Theme.spacing.padding_md,
        )

        # Common pack config
        pack_config = {
            "pady": Theme.spacing.padding_sm,
            "padx": Theme.spacing.padding_sm,
            "fill": "x",
            "expand": False,
        }

        # === Prompt Management Section ===
        prompt_collapsible = CollapsibleFrame(control_panel, "Prompt Management")
        prompt_collapsible.pack(**pack_config)

        prompt_content = prompt_collapsible.get_content_frame()

        prompt_scrollable_frame = ctk.CTkScrollableFrame(
            prompt_content, height=Theme.spacing.scrollable_frame_height
        )
        prompt_scrollable_frame.pack(**pack_config)

        # Prompt button frame
        prompt_button_frame = ctk.CTkFrame(prompt_content)
        prompt_button_frame.pack(**pack_config)

        prompt_new_button = ctk.CTkButton(
            prompt_button_frame,
            text="New",
            command=prompt_callbacks["new"] if prompt_callbacks else None,
            width=Theme.dimensions.button_small,
        )
        prompt_new_button.pack(side="left", padx=Theme.spacing.padding_xs)

        prompt_edit_button = ctk.CTkButton(
            prompt_button_frame,
            text="Edit",
            command=prompt_callbacks["edit"] if prompt_callbacks else None,
            width=Theme.dimensions.button_small,
        )
        prompt_edit_button.pack(side="left", padx=Theme.spacing.padding_xs)

        prompt_delete_button = ctk.CTkButton(
            prompt_button_frame,
            text="Delete",
            command=prompt_callbacks["delete"] if prompt_callbacks else None,
            width=Theme.dimensions.button_small,
        )
        prompt_delete_button.pack(side="left", padx=Theme.spacing.padding_xs)

        # === Game Sessions Section ===
        session_collapsible = CollapsibleFrame(control_panel, "Game Sessions")
        session_collapsible.pack(**pack_config)

        session_content = session_collapsible.get_content_frame()

        session_scrollable_frame = ctk.CTkScrollableFrame(
            session_content, height=Theme.spacing.scrollable_frame_height
        )
        session_scrollable_frame.pack(**pack_config)

        session_new_button = ctk.CTkButton(
            session_content, text="New Game", command=session_callback
        )
        session_new_button.pack(**pack_config)

        # === Advanced Context Section ===
        context_collapsible = CollapsibleFrame(control_panel, "Advanced Context")
        context_collapsible.pack(**pack_config)

        context_content = context_collapsible.get_content_frame()

        ctk.CTkLabel(context_content, text="Author's Note:").pack(
            pady=(Theme.spacing.padding_sm, 0),
            padx=Theme.spacing.padding_sm,
            anchor="w",
        )
        authors_note_textbox = ctk.CTkTextbox(
            context_content, height=Theme.spacing.textbox_huge
        )
        authors_note_textbox.pack(**pack_config)

        ctk.CTkButton(
            context_content, text="💾 Save Author's Note", command=save_context_callback
        ).pack(**pack_config)

        lore_editor_button = ctk.CTkButton(
            context_content, text="Manage Lorebook",
            command=prompt_callbacks.get("world_info") if prompt_callbacks else None,
        )
        lore_editor_button.pack(**pack_config)

        # === Return Widget References ===
        return {
            "control_panel": control_panel,
            "prompt_collapsible": prompt_collapsible,
            "prompt_scrollable_frame": prompt_scrollable_frame,
            "prompt_new_button": prompt_new_button,
            "prompt_edit_button": prompt_edit_button,
            "prompt_delete_button": prompt_delete_button,
            "session_collapsible": session_collapsible,
            "session_scrollable_frame": session_scrollable_frame,
            "session_new_button": session_new_button,
            "authors_note_textbox": authors_note_textbox,
            "world_info_button": lore_editor_button,
        }
