"""
Prompt creation/editing dialog with 3 fields.
"""
import customtkinter as ctk
from app.gui.styles import Theme


class PromptDialog(ctk.CTkToplevel):
    """
    Modal dialog for creating or editing prompts.
    
    Fields:
    - Name: Short identifier for the prompt
    - Content: System prompt that defines AI behavior/world
    - Initial Message: First GM message when starting a new game
    """
    
    def __init__(self, parent, title: str = "New Prompt", existing_prompt=None):
        """
        Args:
            parent: Parent window
            title: Dialog title
            existing_prompt: Prompt object to edit (None for new prompt)
        """
        super().__init__(parent)
        
        self.title(title)
        self.geometry("700x750")
        self.resizable(True, True)
        
        self.result = None  # Will store (name, content, initial_message) tuple
        self.existing_prompt = existing_prompt
        
        self._create_widgets()
        self._load_existing_data()
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        self.focus()
    
    def _create_widgets(self):
        """
        Build the form UI.
        """
        # Main container with padding
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # === Name Field ===
        ctk.CTkLabel(
            main_frame, 
            text="Prompt Name:",
            font=Theme.fonts.subheading,
            anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        self.name_entry = ctk.CTkEntry(
            main_frame,
            placeholder_text="e.g., 'Cyberpunk Adventure', 'Horror Mystery'",
            height=35,
            font=Theme.fonts.body
        )
        self.name_entry.pack(fill="x", pady=(0, 15))
        
        # === Content Field ===
        ctk.CTkLabel(
            main_frame, 
            text="Prompt Content (System Prompt):",
            font=Theme.fonts.subheading,
            anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(
            main_frame,
            text="Define the AI's role, world, tone, and style. This is the 'identity' of your game.",
            font=Theme.fonts.body_small,
            text_color=Theme.colors.text_muted,
            anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        self.content_textbox = ctk.CTkTextbox(
            main_frame,
            height=200,
            font=Theme.fonts.body,
            wrap="word"
        )
        self.content_textbox.pack(fill="both", expand=True, pady=(0, 15))
        
        # === Initial Message Field ===
        ctk.CTkLabel(
            main_frame, 
            text="Initial Message (GM's Opening):",
            font=Theme.fonts.subheading,
            anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(
            main_frame,
            text="The first message the Game Master will say when starting a new game. Should prompt the player for setup info.",
            font=Theme.fonts.body_small,
            text_color=Theme.colors.text_muted,
            anchor="w",
            wraplength=660,
            justify="left"
        ).pack(fill="x", pady=(0, 5))
        
        self.initial_message_textbox = ctk.CTkTextbox(
            main_frame,
            height=120,
            font=Theme.fonts.body,
            wrap="word"
        )
        self.initial_message_textbox.pack(fill="both", expand=True, pady=(0, 15))
        
        # === Buttons ===
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 0))
        
        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=120,
            height=35
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Save Prompt",
            command=self._on_save,
            width=120,
            height=35,
            fg_color=Theme.colors.button_default[0]
        ).pack(side="right", padx=5)
    
    def _load_existing_data(self):
        """Load data from existing prompt if editing."""
        if self.existing_prompt:
            self.name_entry.insert(0, self.existing_prompt.name)
            self.content_textbox.insert("1.0", self.existing_prompt.content)
            self.initial_message_textbox.insert("1.0", self.existing_prompt.initial_message or "")
    
    def _on_save(self):
        """Validate and save the prompt."""
        name = self.name_entry.get().strip()
        content = self.content_textbox.get("1.0", "end-1c").strip()
        initial_message = self.initial_message_textbox.get("1.0", "end-1c").strip()
        
        # Validate required fields
        if not name:
            self._show_error("Prompt name is required")
            return
        
        if not content:
            self._show_error("Prompt content is required")
            return
        
        # Note: initial_message is optional (can be empty)
        
        # Store result and close
        self.result = (name, content, initial_message)
        self.grab_release()
        self.destroy()
    
    def _on_cancel(self):
        """Close without saving."""
        self.result = None
        self.grab_release()
        self.destroy()
    
    def _show_error(self, message: str):
        """Show validation error (simple for now)."""
        error_dialog = ctk.CTkInputDialog(
            text=message,
            title="Validation Error"
        )
        error_dialog.get_input()  # Just to show the message
    
    def get_result(self):
        """
        Get the dialog result after it closes.
        
        Returns:
            Tuple of (name, content, initial_message) or None if cancelled
        """
        return self.result
