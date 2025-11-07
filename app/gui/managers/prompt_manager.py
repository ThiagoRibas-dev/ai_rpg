"""
Manages prompt CRUD operations and UI.

MIGRATION SOURCE: main_view.py lines 621-700
Extracted methods:
- new_prompt() (lines 621-632)
- edit_prompt() (lines 633-645)
- delete_prompt() (lines 646-652)
- on_prompt_select() (lines 653-677)
- refresh_prompt_list() → refresh_list() (lines 678-690)

New responsibilities:
- Create/edit/delete prompts
- Handle prompt selection
- Refresh prompt list UI
- Coordinate with session manager
"""

import customtkinter as ctk
import logging
from typing import Optional
from app.models.prompt import Prompt
from app.gui.styles import get_button_style

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Manages prompt operations and selection.
    
    MIGRATION NOTES:
    - Extracted from: MainView (prompt-related methods lines 621-700)
    - Manages prompt list UI and selection state
    - Coordinates with session manager for prompt selection effects
    """
    
    def __init__(
        self, 
        db_manager,
        prompt_scrollable_frame: ctk.CTkScrollableFrame,
        prompt_collapsible
    ):
        """
        Initialize the prompt manager.
        
        MIGRATION NOTES:
        - All parameters previously accessed via self.* in MainView
        - db_manager: Previously self.db_manager
        - prompt_scrollable_frame: Previously self.prompt_scrollable_frame
        - prompt_collapsible: Previously self.prompt_collapsible
        
        Args:
            db_manager: Database manager instance
            prompt_scrollable_frame: Frame for displaying prompt list
            prompt_collapsible: Collapsible frame container
        """
        self.db_manager = db_manager
        self.prompt_scrollable_frame = prompt_scrollable_frame
        self.prompt_collapsible = prompt_collapsible
        self._selected_prompt: Optional[Prompt] = None
        self.session_manager = None  # Will be set by MainView.set_orchestrator
    
    @property
    def selected_prompt(self) -> Optional[Prompt]:
        """
        Get the currently selected prompt.
        
        MIGRATION NOTES:
        - Previously: MainView.selected_prompt (line 28)
        - Now: Property on PromptManager
        """
        return self._selected_prompt
    
    def set_session_manager(self, session_manager):
        """
        Wire the session manager for cross-manager coordination.
        
        NEW METHOD:
        - Called from: MainView.set_orchestrator()
        - Enables on_prompt_select to trigger session list refresh
        """
        self.session_manager = session_manager
    
    def new_prompt(self):
        """
        Create a new prompt via dialog.
        
        MIGRATION NOTES:
        - Extracted from: MainView.new_prompt() lines 621-632
        - Uses self.db_manager instead of self.db_manager (no change)
        - Calls self.refresh_list (was self.refresh_prompt_list)
        """
        # Prompt for name
        dialog = ctk.CTkInputDialog(text="Enter prompt name:", title="New Prompt")
        name = dialog.get_input()
        
        if name:
            # Prompt for content
            content_dialog = ctk.CTkInputDialog(text="Enter prompt content:", title="New Prompt")
            content = content_dialog.get_input()
            
            if content:
                # Create in database
                self.db_manager.create_prompt(name, content)
                # Refresh list
                self.refresh_list()
    
    def edit_prompt(self):
        """
        Edit the selected prompt via dialog.
        
        MIGRATION NOTES:
        - Extracted from: MainView.edit_prompt() lines 633-645
        - Changed: Uses self._selected_prompt instead of parameter
        - Calls self.refresh_list (was self.refresh_prompt_list)
        """
        if not self._selected_prompt:
            return
        
        # Prompt for new name
        name_dialog = ctk.CTkInputDialog(text="Enter new name:", title="Edit Prompt")
        name = name_dialog.get_input()
        
        if name:
            # Prompt for new content
            content_dialog = ctk.CTkInputDialog(text="Enter new content:", title="Edit Prompt")
            content = content_dialog.get_input()
            
            if content:
                # Update prompt object
                self._selected_prompt.name = name
                self._selected_prompt.content = content
                # Save to database
                self.db_manager.update_prompt(self._selected_prompt)
                # Refresh list
                self.refresh_list()
    
    def delete_prompt(self):
        """
        Delete the selected prompt.
        
        MIGRATION NOTES:
        - Extracted from: MainView.delete_prompt() lines 646-652
        - Changed: Uses self._selected_prompt instead of parameter
        - Calls self.refresh_list (was self.refresh_prompt_list)
        """
        if not self._selected_prompt:
            return
        
        # Delete from database
        self.db_manager.delete_prompt(self._selected_prompt.id)
        # Clear selection
        self._selected_prompt = None
        # Refresh list
        self.refresh_list()
    
    def on_prompt_select(self, prompt: Prompt, session_manager):
        """
        Handle prompt selection.
        
        MIGRATION NOTES:
        - Extracted from: MainView.on_prompt_select() lines 653-677
        - Changed: Requires session_manager parameter (was self.session_manager)
        - Changed: self.selected_session = None → session_manager (coordination)
        - Changed: self.send_button.configure → session_manager handles this
        
        Args:
            prompt: Selected prompt
            session_manager: SessionManager instance for refreshing session list
        """
        # Store selection
        self._selected_prompt = prompt
        
        # Refresh session list for this prompt
        # MIGRATED FROM: line 657
        session_manager.refresh_session_list(prompt.id)
        
        # Update button styles
        # MIGRATED FROM: lines 659-666
        button_styles = get_button_style()
        selected_style = get_button_style("selected")
        
        for widget in self.prompt_scrollable_frame.winfo_children():
            if widget.cget("text") == prompt.name:
                widget.configure(fg_color=selected_style["fg_color"])
            else:
                widget.configure(fg_color=button_styles["fg_color"])
        
        # Collapse the prompt panel
        # MIGRATED FROM: lines 668-669
        if self.prompt_collapsible and not self.prompt_collapsible.is_collapsed:
            self.prompt_collapsible.toggle()
    
    def refresh_list(self):
        """
        Refresh the prompt list UI.
        
        MIGRATION NOTES:
        - Extracted from: MainView.refresh_prompt_list() lines 678-690
        - Renamed: refresh_prompt_list → refresh_list (shorter)
        - Changed: Button command uses _on_button_click (internal handler)
        """
        # Clear existing widgets
        for widget in self.prompt_scrollable_frame.winfo_children():
            widget.destroy()
        
        # Get all prompts from database
        prompts = self.db_manager.get_all_prompts()
        
        # Create button for each prompt
        for prompt in prompts:
            btn = ctk.CTkButton(
                self.prompt_scrollable_frame, 
                text=prompt.name,
                command=lambda p=prompt: self._on_button_click(p)
            )
            btn.pack(pady=2, padx=5, fill="x")
    
    def _on_button_click(self, prompt: Prompt):
        """
        Internal handler for prompt button clicks.
        
        NEW METHOD:
        - Calls on_prompt_select with session_manager if available
        - Otherwise logs warning
        """
        if self.session_manager:
            self.on_prompt_select(prompt, self.session_manager)
        else:
            logger.warning("Prompt button clicked but session_manager not wired yet")
