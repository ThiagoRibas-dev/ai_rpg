"""
Builds the control (right) panel of the application.

MIGRATION SOURCE: main_view.py lines 281-450 (_create_right_panel_widgets)
Extracted sections:
- Control panel frame (lines 285-290)
- Prompt Management section (lines 295-325)
- Game Sessions section (lines 330-345)
- Advanced Context section (lines 350-385)
- Game State Inspector tabs (lines 390-450)

New responsibilities:
- Create all control panel widgets
- Return widget references as dictionary
- Accept callbacks from parent (to wire to managers later)
"""

import customtkinter as ctk
from typing import Dict, Any, Callable, Optional
from app.gui.collapsible_frame import CollapsibleFrame
from app.gui.styles import Theme


class ControlPanelBuilder:
    """
    Static factory for building the control (right) panel.
    
    Returns a dictionary of widget references for the MainView to store.
    """
    
    @staticmethod
    def build(
        parent: ctk.CTk,
        prompt_callbacks: Optional[Dict[str, Callable]],
        session_callback: Optional[Callable],
        world_info_callback: Callable,
        save_context_callback: Callable
    ) -> Dict[str, Any]:
        """
        Build the control panel and return widget references.
        
        MIGRATION NOTES:
        - Extracted from: MainView._create_right_panel_widgets() lines 281-450
        - Callbacks may be None initially (wired in set_orchestrator)
        - All button commands are conditional to allow late binding
        
        Args:
            parent: The main window to attach widgets to
            prompt_callbacks: Dict with 'new', 'edit', 'delete' callbacks (or None)
            session_callback: Callback for new game button (or None)
            world_info_callback: Callback for world info button
            save_context_callback: Callback for save context button
        
        Returns:
            Dictionary containing all control panel widget references:
            {
                'control_panel': CTkScrollableFrame,
                'prompt_collapsible': CollapsibleFrame,
                'prompt_scrollable_frame': CTkScrollableFrame,
                'prompt_new_button': CTkButton,  # NEW: Store for rewiring
                'prompt_edit_button': CTkButton,  # NEW: Store for rewiring
                'prompt_delete_button': CTkButton,  # NEW: Store for rewiring
                'session_collapsible': CollapsibleFrame,
                'session_scrollable_frame': CTkScrollableFrame,
                'session_new_button': CTkButton,  # NEW: Store for rewiring
                'memory_textbox': CTkTextbox,
                'authors_note_textbox': CTkTextbox,
                'game_state_inspector_tabs': CTkTabview,
            }
        """
        # === Control Panel (Scrollable) ===
        # MIGRATED FROM: lines 285-290
        control_panel = ctk.CTkScrollableFrame(parent, fg_color=Theme.colors.bg_primary)
        control_panel.grid(row=0, column=1, sticky="nsew", 
                          padx=(0, Theme.spacing.padding_md), 
                          pady=Theme.spacing.padding_md)
        
        # Common pack config
        pack_config = {
            "pady": Theme.spacing.padding_sm,
            "padx": Theme.spacing.padding_sm,
            "fill": "x",
            "expand": False
        }
        
        # === Prompt Management Section ===
        # MIGRATED FROM: lines 295-325
        prompt_collapsible = CollapsibleFrame(control_panel, "Prompt Management")
        prompt_collapsible.pack(**pack_config)
        
        prompt_content = prompt_collapsible.get_content_frame()
        
        prompt_scrollable_frame = ctk.CTkScrollableFrame(
            prompt_content, 
            height=Theme.spacing.scrollable_frame_height
        )
        prompt_scrollable_frame.pack(**pack_config)
        
        # Prompt button frame
        # MIGRATED FROM: lines 310-325
        prompt_button_frame = ctk.CTkFrame(prompt_content)
        prompt_button_frame.pack(**pack_config)
        
        # CHANGED: Store button references for later rewiring
        prompt_new_button = ctk.CTkButton(
            prompt_button_frame, 
            text="New", 
            command=prompt_callbacks['new'] if prompt_callbacks else None,
            width=Theme.dimensions.button_small
        )
        prompt_new_button.pack(side="left", padx=Theme.spacing.padding_xs)
        
        prompt_edit_button = ctk.CTkButton(
            prompt_button_frame, 
            text="Edit", 
            command=prompt_callbacks['edit'] if prompt_callbacks else None,
            width=Theme.dimensions.button_small
        )
        prompt_edit_button.pack(side="left", padx=Theme.spacing.padding_xs)
        
        prompt_delete_button = ctk.CTkButton(
            prompt_button_frame, 
            text="Delete", 
            command=prompt_callbacks['delete'] if prompt_callbacks else None,
            width=Theme.dimensions.button_small
        )
        prompt_delete_button.pack(side="left", padx=Theme.spacing.padding_xs)
        
        # === Game Sessions Section ===
        # MIGRATED FROM: lines 330-345
        session_collapsible = CollapsibleFrame(control_panel, "Game Sessions")
        session_collapsible.pack(**pack_config)
        
        session_content = session_collapsible.get_content_frame()
        
        session_scrollable_frame = ctk.CTkScrollableFrame(
            session_content, 
            height=Theme.spacing.scrollable_frame_height
        )
        session_scrollable_frame.pack(**pack_config)
        
        # CHANGED: Store button reference for later rewiring
        session_new_button = ctk.CTkButton(
            session_content, 
            text="New Game", 
            command=session_callback
        )
        session_new_button.pack(**pack_config)
        
        # === Advanced Context Section ===
        # MIGRATED FROM: lines 350-385
        context_collapsible = CollapsibleFrame(control_panel, "Advanced Context")
        context_collapsible.pack(**pack_config)
        
        context_content = context_collapsible.get_content_frame()
        
        # Memory textbox
        # MIGRATED FROM: lines 355-360
        ctk.CTkLabel(context_content, text="Memory:").pack(
            pady=(Theme.spacing.padding_sm, 0), 
            padx=Theme.spacing.padding_sm, 
            anchor="w"
        )
        memory_textbox = ctk.CTkTextbox(context_content, height=Theme.spacing.textbox_small)
        memory_textbox.pack(**pack_config)
        
        # Author's Note textbox
        # MIGRATED FROM: lines 362-367
        ctk.CTkLabel(context_content, text="Author's Note:").pack(
            pady=(Theme.spacing.padding_sm, 0), 
            padx=Theme.spacing.padding_sm, 
            anchor="w"
        )
        authors_note_textbox = ctk.CTkTextbox(context_content, height=Theme.spacing.textbox_small)
        authors_note_textbox.pack(**pack_config)
        
        # World Info button
        # MIGRATED FROM: lines 369-372
        ctk.CTkButton(
            context_content, 
            text="Manage World Info", 
            command=world_info_callback
        ).pack(**pack_config)
        
        # Save Context button
        # MIGRATED FROM: lines 374-377
        ctk.CTkButton(
            context_content, 
            text="Save Context", 
            command=save_context_callback
        ).pack(**pack_config)
        
        # === Game State Inspector Section ===
        # MIGRATED FROM: lines 390-450
        inspector_collapsible = CollapsibleFrame(control_panel, "Game State Inspector")
        inspector_collapsible.pack(
            pady=Theme.spacing.padding_sm, 
            padx=Theme.spacing.padding_sm, 
            fill="both", 
            expand=True
        )
        
        inspector_content = inspector_collapsible.get_content_frame()
        
        # Create tab view
        # MIGRATED FROM: lines 400-450
        game_state_inspector_tabs = ctk.CTkTabview(inspector_content)
        game_state_inspector_tabs.pack(fill="both", expand=True)
        
        # Add tabs (actual inspector views are created by InspectorManager)
        game_state_inspector_tabs.add("Characters")
        game_state_inspector_tabs.add("Inventory")
        game_state_inspector_tabs.add("Quests")
        game_state_inspector_tabs.add("Memories")
        game_state_inspector_tabs.add("Tool Calls")
        game_state_inspector_tabs.add("State Viewer")
        
        # === Return Widget References ===
        # NEW: Return all widgets as dictionary for parent to store
        return {
            'control_panel': control_panel,
            'prompt_collapsible': prompt_collapsible,
            'prompt_scrollable_frame': prompt_scrollable_frame,
            'prompt_new_button': prompt_new_button,  # NEW: For rewiring
            'prompt_edit_button': prompt_edit_button,  # NEW: For rewiring
            'prompt_delete_button': prompt_delete_button,  # NEW: For rewiring
            'session_collapsible': session_collapsible,
            'session_scrollable_frame': session_scrollable_frame,
            'session_new_button': session_new_button,  # NEW: For rewiring
            'memory_textbox': memory_textbox,
            'authors_note_textbox': authors_note_textbox,
            'game_state_inspector_tabs': game_state_inspector_tabs,
        }
