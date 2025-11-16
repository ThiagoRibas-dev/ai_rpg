"""
Manages prompt CRUD operations and UI.

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
from app.gui.world_info_manager_view import WorldInfoManagerView

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Manages prompt operations and selection.
    """

    def __init__(
        self,
        db_manager,
        orchestrator,
        prompt_scrollable_frame: ctk.CTkScrollableFrame,
        # COMMENT: We need the main view (parent window) to create the modal dialog.
        parent_view: ctk.CTk,
        prompt_collapsible,
    ):
        """
        Initializes the PromptManager.

        Args:
            db_manager: Database manager instance
            orchestrator: Orchestrator instance
            prompt_scrollable_frame: Frame for displaying prompt list
            prompt_collapsible: Collapsible frame container
        """
        self.db_manager = db_manager
        self.orchestrator = orchestrator
        self.prompt_scrollable_frame = prompt_scrollable_frame
        self.prompt_collapsible = prompt_collapsible
        self._selected_prompt: Optional[Prompt] = None
        self.session_manager = None  # Will be set by MainView.set_orchestrator

    @property
    def selected_prompt(self) -> Optional[Prompt]:
        """
        Get the currently selected prompt.
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

    def set_orchestrator(self, orchestrator): # Add this method
        """Set the orchestrator instance."""
        self.orchestrator = orchestrator

    def new_prompt(self):
        """
        Create a new prompt via 3-field dialog.
        """
        from app.gui.panels.prompt_dialog import PromptDialog

        # Get the LLM connector
        llm_connector = self.orchestrator._get_llm_connector()

        dialog = PromptDialog(
            self.prompt_scrollable_frame.winfo_toplevel(),
            title="New Prompt",
            llm_connector=llm_connector # Pass connector to dialog
        )
        self.prompt_scrollable_frame.wait_window(dialog)  # Wait for dialog to close

        result = dialog.get_result()
        if result:
            name, content, initial_message, rules_document, template_manifest = result

            # Create in database
            self.db_manager.create_prompt(name, content, initial_message, rules_document, template_manifest)

            # Refresh list
            self.refresh_list()

    def edit_prompt(self):
        """
        Edit the selected prompt via 3-field dialog.
        """
        if not self._selected_prompt:
            return

        from app.gui.panels.prompt_dialog import PromptDialog

        # Get the LLM connector
        llm_connector = self.orchestrator._get_llm_connector()

        dialog = PromptDialog(
            self.prompt_scrollable_frame.winfo_toplevel(),
            title="Edit Prompt",
            existing_prompt=self._selected_prompt,
            llm_connector=llm_connector # Pass connector to dialog
        )
        self.prompt_scrollable_frame.wait_window(dialog)  # Wait for dialog to close

        result = dialog.get_result()
        if result:
            name, content, initial_message, rules_document, template_manifest = result

            # Update prompt object
            self._selected_prompt.name = name
            self._selected_prompt.content = content
            self._selected_prompt.initial_message = initial_message
            self._selected_prompt.rules_document = rules_document
            self._selected_prompt.template_manifest = template_manifest

            # Save to database
            self.db_manager.update_prompt(self._selected_prompt)

            # Refresh list
            self.refresh_list()

    def delete_prompt(self):
        """
        Delete the selected prompt.
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

        Args:
            prompt: Selected prompt
            session_manager: SessionManager instance for refreshing session list
        """
        # Store selection
        self._selected_prompt = prompt

        # Refresh session list for this prompt
        session_manager.refresh_session_list(prompt.id)

        # Update button styles
        button_styles = get_button_style()
        selected_style = get_button_style("selected")

        for widget in self.prompt_scrollable_frame.winfo_children():
            if widget.cget("text") == prompt.name:
                widget.configure(fg_color=selected_style["fg_color"])
            else:
                widget.configure(fg_color=button_styles["fg_color"])

        # Collapse the prompt panel
        if self.prompt_collapsible and not self.prompt_collapsible.is_collapsed:
            self.prompt_collapsible.toggle()

    def refresh_list(self):
        """
        Refresh the prompt list UI.
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
                command=lambda p=prompt: self._on_button_click(p),
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

    def open_world_info_manager(self):
        """
        Open world info manager dialog.
        COMMENT: This logic is moved from MainView. It belongs here because
        World Info is tied to the currently selected prompt.
        """
        if not self.selected_prompt:
            # We need a bubble manager reference to show this message.
            # This will be wired in MainView.
            if hasattr(self, 'bubble_manager') and self.bubble_manager:
                self.bubble_manager.add_message("system", "Please select a prompt first")
            return

        world_info_view = WorldInfoManagerView(
            self.parent_view,
            self.db_manager,
            self.selected_prompt.id,
            getattr(self.orchestrator, "vector_store", None),
        )
        world_info_view.grab_set()
