"""
Prompt creation/editing dialog with 3 fields.
"""

import customtkinter as ctk
import logging # ✅ NEW: Import logging
from typing import Optional # ✅ NEW: Import Optional
from app.gui.styles import Theme
from app.llm.llm_connector import LLMConnector


class PromptDialog(ctk.CTkToplevel):
    """
    Modal dialog for creating or editing prompts.

    Fields:
    - Name: Short identifier for the prompt
    - Content: System prompt that defines AI behavior/world
    """
 
    def __init__(self, parent, title: str = "New Prompt", existing_prompt=None, llm_connector: Optional[LLMConnector] = None):
        """
        Args:
            parent: Parent window
            title: Dialog title
            existing_prompt: Prompt object to edit (None for new prompt)
            llm_connector: The LLMConnector instance for AI operations
        """
        super().__init__(parent)

        self.title(title)
        self.geometry("1024x720")
        self.resizable(True, True)
 
        self.result = None  # Will store (name, content, rules, template) tuple
        self.existing_prompt = existing_prompt
        self.llm_connector = llm_connector # ✅ NEW: Store the connector

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
        main_frame = ctk.CTkScrollableFrame(self) # <-- Changed from CTkFrame
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # === Name Field ===
        ctk.CTkLabel(
            main_frame, text="Prompt Name:", font=Theme.fonts.subheading, anchor="w"
        ).pack(fill="x", pady=(0, 5))

        self.name_entry = ctk.CTkEntry(
            main_frame,
            placeholder_text="e.g., 'Cyberpunk Adventure', 'Horror Mystery'",
            height=35,
            font=Theme.fonts.body,
        )
        self.name_entry.pack(fill="x", pady=(0, 15))

        # === Content Field ===
        ctk.CTkLabel(
            main_frame,
            text="Prompt Content (System Prompt):",
            font=Theme.fonts.subheading,
            anchor="w",
        ).pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(
            main_frame,
            text="Define the AI's role, world, tone, and style. This is the 'identity' of your game.",
            font=Theme.fonts.body_small,
            text_color=Theme.colors.text_muted,
            anchor="w",
        ).pack(fill="x", pady=(0, 5))

        self.content_textbox = ctk.CTkTextbox(
            main_frame, height=200, font=Theme.fonts.body, wrap="word"
        )
        self.content_textbox.pack(fill="both", expand=True, pady=(0, 15))
 
        # ✅ NEW: Rules Document Section
        rules_label = ctk.CTkLabel(
            main_frame,
            text="Rules Document (optional - AI will extract game mechanics):",
            font=Theme.fonts.subheading,
            anchor="w"
        )
        rules_label.pack(fill="x", pady=(0, 5))

        rules_hint = ctk.CTkLabel(
            main_frame,
            text="Paste SRD text, homebrew rules, or describe your system. AI will generate properties from this.",
            font=Theme.fonts.body_small,
            text_color=Theme.colors.text_muted,
            anchor="w",
            wraplength=660,
            justify="left",
        )
        rules_hint.pack(fill="x", pady=(0, 5))

        self.rules_textbox = ctk.CTkTextbox(main_frame, height=200, font=Theme.fonts.body, wrap="word")
        self.rules_textbox.pack(fill="both", expand=True, pady=(0, 15))

        # ✅ NEW: Generate Template Button
        generate_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        generate_frame.pack(fill="x", pady=(0, 15))

        self.generate_btn = ctk.CTkButton(
            generate_frame,
            text="🤖 Generate Template from Rules",
            command=self._generate_template,
            height=35,
            font=Theme.fonts.subheading
        )
        self.generate_btn.pack(side="left", padx=5)

        self.generate_status = ctk.CTkLabel(
            generate_frame,
            text="",
            font=Theme.fonts.body_small,
            text_color=Theme.colors.text_muted
        )
        self.generate_status.pack(side="left", padx=10)

        # ✅ NEW: Template Preview
        template_label = ctk.CTkLabel(
            main_frame,
            text="Generated Template (review and edit if needed):",
            font=Theme.fonts.subheading,
            anchor="w"
        )
        template_label.pack(fill="x", pady=(0, 5))

        self.template_textbox = ctk.CTkTextbox(main_frame, height=200, font=Theme.fonts.body, wrap="word")
        self.template_textbox.pack(fill="both", expand=True, pady=(0, 15))

        # === Buttons ===
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            button_frame, text="Cancel", command=self._on_cancel, width=120, height=35
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Save Prompt",
            command=self._on_save,
            width=120,
            height=35,
            fg_color=Theme.colors.button_default[0],
        ).pack(side="right", padx=5)

    def _update_generation_status(self, message: str):
        """GUI thread-safe method to update the status label."""
        self.generate_status.configure(text=message, text_color="gray")

    def _generate_template(self):
        """Generate template from rules document using AI."""
        import threading
        
        rules_text = self.rules_textbox.get("1.0", "end-1c").strip()
        
        if not rules_text:
            self.generate_status.configure(
                text="⚠️ Please enter rules document first",
                text_color="orange"
            )
            return
        
        self.generate_status.configure(text="🔄 Analyzing rules...", text_color="gray")
        self.generate_btn.configure(state="disabled")
        
        # Run in background thread
        thread = threading.Thread(
            target=self._generate_template_background,
            args=(rules_text,),
            daemon=True
        )
        thread.start()

    def _generate_template_background(self, rules_text: str):
        """
        Background thread for AI processing.
        Now returns a tuple: (ruleset_dict, stat_template_dict) wrapped in a container dict for the UI.
        """
        try:
            from app.setup.template_generation_service import TemplateGenerationService
            
            if not self.llm_connector:
                raise ValueError("LLMConnector not provided to PromptDialog")

            generator = TemplateGenerationService(
                self.llm_connector, 
                rules_text, 
                status_callback=lambda msg: self.after(0, self._update_generation_status, msg)
            )
            
            # Returns (Ruleset, StatBlockTemplate) models
            ruleset, stat_template = generator.generate_template()
            
            # Combine for display in the single text box (temporary visualization)
            combined_result = {
                "ruleset": ruleset.model_dump(exclude_none=True),
                "stat_template": stat_template.model_dump(exclude_none=True)
            }
            
            # Update final UI on main thread
            self.after(0, self._on_template_generated, combined_result, None)
            
        except Exception as e:
            logging.exception("Template generation failed in background thread")
            self.after(0, self._on_template_generated, None, str(e))

    def _on_template_generated(self, template: dict | None, error: str | None):
        """Handle template generation result."""
        import json
        
        self.generate_btn.configure(state="normal")
        
        if error:
            self.generate_status.configure(
                text=f"❌ Error: {error}",
                text_color="red"
            )
            return
        
        if template:
            # Pretty print JSON
            template_json = json.dumps(template, indent=2)
            self.template_textbox.delete("1.0", "end")
            self.template_textbox.insert("1.0", template_json)
            
            # Calculate property count for status using the NEW structure
            prop_count = 0
            
            # 1. Count Ruleset items
            ruleset = template.get("ruleset", {})
            compendium = ruleset.get("compendium", {})
            prop_count += len(compendium.get("skills", []))
            prop_count += len(compendium.get("conditions", []))
            prop_count += len(ruleset.get("tactical_rules", []))
            
            # 2. Count Stat Template items
            stat_template = template.get("stat_template", {})
            prop_count += len(stat_template.get("abilities", []))
            prop_count += len(stat_template.get("vitals", []))
            prop_count += len(stat_template.get("tracks", []))
            prop_count += len(stat_template.get("slots", []))
            
            self.generate_status.configure(
                text=f"✅ Generated {prop_count} properties",
                text_color="green"
            )

    def _load_existing_data(self):
        """Load data from existing prompt if editing."""
        if self.existing_prompt:
            self.name_entry.insert(0, self.existing_prompt.name)
            self.content_textbox.insert("1.0", self.existing_prompt.content)
            
            # ✅ NEW: Load rules document and template
            self.rules_textbox.insert("1.0", self.existing_prompt.rules_document or "")
            self.template_textbox.insert("1.0", self.existing_prompt.template_manifest or "{}")

    def _on_save(self):
        """Validate and save the prompt."""
        name = self.name_entry.get().strip()
        content = self.content_textbox.get("1.0", "end-1c").strip()
        rules_document = self.rules_textbox.get("1.0", "end-1c").strip()
        template_manifest = self.template_textbox.get("1.0", "end-1c").strip()
        
        # Validate required fields
        if not name:
            self._show_error("Prompt name is required")
            return
 
        if not content:
            self._show_error("Prompt content is required")
            return
 
        # Store result and close
        self.result = (name, content, rules_document, template_manifest)
        self.grab_release()
        self.destroy()

    def _on_cancel(self):
        """Close without saving."""
        self.result = None
        self.grab_release()
        self.destroy()

    def _show_error(self, message: str):
        """Show validation error (simple for now)."""
        error_dialog = ctk.CTkInputDialog(text=message, title="Validation Error")
        error_dialog.get_input()  # Just to show the message

    def get_result(self):
        """
        Get the dialog result after it closes.
 
        Returns:
            Tuple of (name, content, rules_document, template_manifest) or None if cancelled
        """
        return self.result
