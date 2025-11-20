"""
Builds the main (left) panel of the application.

New responsibilities:
- Create all main panel widgets
- Return widget references as dictionary
- No business logic (pure UI construction)
"""

import customtkinter as ctk
from typing import Dict, Any, Callable
from app.gui.styles import Theme


class MainPanelBuilder:
    """
    Static factory for building the main (left) panel.

    Returns a dictionary of widget references for the MainView to store.
    """

    @staticmethod
    def build(parent: ctk.CTk, send_callback: Callable) -> Dict[str, Any]:
        """
        Build the main panel and return widget references.

        Args:
            parent: The main window to attach widgets to
            send_callback: Callback for the send button

        Returns:
            Dictionary containing all main panel widget references.
        """
        # === Main Panel Frame ===
        main_panel = ctk.CTkFrame(parent, fg_color=Theme.colors.bg_primary)
        main_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=Theme.spacing.padding_md,
            pady=Theme.spacing.padding_md,
        )
        main_panel.grid_rowconfigure(1, weight=1)  # chat takes the space
        main_panel.grid_columnconfigure(0, weight=1)

        # === Game Time Header Bar ===
        game_time_frame = ctk.CTkFrame(
            main_panel, fg_color=Theme.colors.bg_tertiary, height=40
        )
        game_time_frame.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=Theme.spacing.padding_sm,
            pady=(Theme.spacing.padding_sm, 0),
        )
        game_time_frame.grid_propagate(False)

        # Left: Game time label
        game_time_label = ctk.CTkLabel(
            game_time_frame,
            text="🕐 Day 1, Dawn",
            font=Theme.fonts.subheading,
            text_color=Theme.colors.text_gold,
        )
        game_time_label.pack(
            side="left", padx=Theme.spacing.padding_md, pady=Theme.spacing.padding_sm
        )

        # Center: Game mode indicator
        game_mode_label = ctk.CTkLabel(
            game_time_frame,
            text="📋 SETUP",
            font=Theme.fonts.subheading,
            text_color=Theme.colors.text_secondary,
        )
        game_mode_label.pack(
            side="left",
            expand=True,
            padx=Theme.spacing.padding_md,
            pady=Theme.spacing.padding_sm,
        )

        # Right: Session name
        session_name_label = ctk.CTkLabel(
            game_time_frame,
            text="No session loaded",
            font=Theme.fonts.body_small,
            text_color=Theme.colors.text_muted,
        )
        session_name_label.pack(
            side="right", padx=Theme.spacing.padding_md, pady=Theme.spacing.padding_sm
        )

        # === Chat History Frame ===
        chat_history_frame = ctk.CTkScrollableFrame(
            main_panel, fg_color=Theme.colors.bg_secondary
        )
        chat_history_frame.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="nsew",
            padx=Theme.spacing.padding_sm,
            pady=Theme.spacing.padding_sm,
        )

        # === Choice Button Frame ===
        choice_button_frame = ctk.CTkFrame(main_panel)
        choice_button_frame.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=Theme.spacing.padding_sm,
            pady=Theme.spacing.padding_sm,
        )
        choice_button_frame.grid_remove()  # Hidden by default

        # === Loading Indicator ===
        loading_frame = ctk.CTkFrame(main_panel, fg_color=Theme.colors.bg_tertiary)
        loading_label = ctk.CTkLabel(
            loading_frame,
            text="🤔 AI is thinking...",
            font=Theme.fonts.subheading,
            text_color=Theme.colors.text_gold,
        )
        loading_label.pack(pady=10)
        # Note: Don't grid yet - will be shown/hidden by UIQueueHandler

        # === History Control Toolbar ===
        history_toolbar = ctk.CTkFrame(main_panel)
        history_toolbar.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=Theme.spacing.padding_sm,
            pady=(Theme.spacing.padding_sm, 0),
        )
        history_toolbar.grid_remove()  # Hidden by default, shown when session loaded

        reroll_button = ctk.CTkButton(
            history_toolbar,
            text="🔄 Reroll",
            width=80,
            height=28,
            command=None,  # Will be wired later
        )
        reroll_button.pack(side="left", padx=2)

        delete_last_button = ctk.CTkButton(
            history_toolbar,
            text="🗑️ Delete Last",
            width=100,
            height=28,
            command=None,  # Will be wired later
        )
        delete_last_button.pack(side="left", padx=2)

        trim_button = ctk.CTkButton(
            history_toolbar,
            text="✂️ Trim...",
            width=80,
            height=28,
            command=None,  # Will be wired later
        )
        trim_button.pack(side="left", padx=2)

        # History info label (shows message count)
        history_info_label = ctk.CTkLabel(
            history_toolbar,
            text="0 messages",
            font=Theme.fonts.body_small,
            text_color=Theme.colors.text_muted,
        )
        history_info_label.pack(side="right", padx=10)

        # === User Input ===
        user_input = ctk.CTkTextbox(main_panel, height=Theme.spacing.input_height)
        user_input.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=Theme.spacing.padding_sm,
            pady=Theme.spacing.padding_sm,
        )

        # === Button Frame ===
        button_frame = ctk.CTkFrame(main_panel)
        button_frame.grid(
            row=4,
            column=1,
            sticky="ns",
            padx=Theme.spacing.padding_sm,
            pady=Theme.spacing.padding_sm,
        )

        send_button = ctk.CTkButton(
            button_frame, text="Send", state="disabled", command=send_callback
        )
        send_button.pack(
            expand=True,
            fill="both",
            padx=Theme.spacing.padding_xs,
            pady=Theme.spacing.padding_xs,
        )

        stop_button = ctk.CTkButton(button_frame, text="Stop")
        stop_button.pack(
            expand=True,
            fill="both",
            padx=Theme.spacing.padding_xs,
            pady=Theme.spacing.padding_xs,
        )

        # === Return Widget References ===
        return {
            "main_panel": main_panel,
            "game_time_frame": game_time_frame,
            "game_time_label": game_time_label,
            "game_mode_label": game_mode_label,
            "session_name_label": session_name_label,
            "chat_history_frame": chat_history_frame,
            "choice_button_frame": choice_button_frame,
            "loading_frame": loading_frame,
            "loading_label": loading_label,
            "history_toolbar": history_toolbar,
            "reroll_button": reroll_button,
            "delete_last_button": delete_last_button,
            "trim_button": trim_button,
            "history_info_label": history_info_label,
            "user_input": user_input,
            "send_button": send_button,
            "stop_button": stop_button,
        }
