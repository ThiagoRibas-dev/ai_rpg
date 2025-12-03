from nicegui import ui
import json
import asyncio
from app.models.prompt import Prompt
from app.setup.rules_generator import RulesGenerator
import logging

logger = logging.getLogger(__name__)


class PromptEditorDialog:
    def __init__(self, db_manager, orchestrator, prompt: Prompt = None, on_save=None):
        self.db = db_manager
        self.orchestrator = orchestrator
        self.prompt = prompt
        self.on_save = on_save
        self.dialog = ui.dialog()

        # State
        self.name = prompt.name if prompt else ""
        self.content = prompt.content if prompt else ""
        self.rules = prompt.rules_document if prompt else ""

        # Load existing ruleset JSON if present
        self.ruleset_json = "{}"
        if prompt and prompt.template_manifest:
            try:
                # Check if it's wrapped in 'ruleset' key or raw
                data = json.loads(prompt.template_manifest)
                if "ruleset" in data:
                    self.ruleset_json = json.dumps(data["ruleset"], indent=2)
                else:
                    self.ruleset_json = prompt.template_manifest
            except Exception as e:
                logger.warning(f"Failed to load existing ruleset JSON: {e}")
                pass

        # UI Refs
        self.status_label = None
        self.gen_btn = None

    def open(self):
        with (
            self.dialog,
            ui.card().classes(
                "w-[1200px] h-[800px] bg-slate-900 border border-slate-700 p-0"
            ),
        ):
            # Header
            with ui.row().classes(
                "w-full bg-slate-950 p-4 justify-between items-center border-b border-slate-700"
            ):
                title = "Edit Prompt" if self.prompt else "Create Prompt"
                ui.label(title).classes("text-xl font-bold text-white")
                ui.button(icon="close", on_click=self.dialog.close).props(
                    "flat dense round"
                )

            # Body: Split View
            with ui.row().classes("w-full h-full gap-0"):
                # LEFT COLUMN: Text Inputs
                with ui.column().classes(
                    "w-1/2 h-full p-4 border-r border-slate-800 scroll-y gap-4"
                ):
                    ui.input(label="System Name").bind_value(self, "name").classes(
                        "w-full"
                    )

                    ui.label("System Instruction (The Persona)").classes(
                        "text-xs font-bold text-gray-500 uppercase mt-2"
                    )
                    ui.textarea(placeholder="You are the GM...").bind_value(
                        self, "content"
                    ).classes("w-full").props("rows=4 outlined")

                    ui.label("Rules Document (The Knowledge Base)").classes(
                        "text-xs font-bold text-gray-500 uppercase mt-2"
                    )
                    ui.label("Paste raw text rules here.").classes(
                        "text-xs text-gray-600 italic"
                    )
                    ui.textarea(placeholder="Paste rules text here...").bind_value(
                        self, "rules"
                    ).classes("w-full flex-grow").props("rows=10 outlined")

                # RIGHT COLUMN: Rules Extraction
                with ui.column().classes("w-1/2 h-full p-4 flex flex-col"):
                    ui.label("System Mechanics (JSON)").classes(
                        "text-xs font-bold text-gray-500 uppercase"
                    )
                    ui.label(
                        "Extracted logic used by the Game Engine (Dice, Procedures)."
                    ).classes("text-xs text-gray-600 italic")

                    # Toolbar
                    with ui.row().classes("w-full items-center gap-2 mb-2"):
                        self.gen_btn = (
                            ui.button("Extract Rules", on_click=self.run_extraction)
                            .classes("bg-purple-700 text-xs")
                            .props("icon=auto_awesome")
                        )
                        self.status_label = ui.label("").classes(
                            "text-xs text-green-400"
                        )

                    # Editor
                    ui.textarea().bind_value(self, "ruleset_json").classes(
                        "w-full h-full font-mono text-xs"
                    ).props('outlined input-class="h-full"')

            # Footer
            with ui.row().classes(
                "w-full bg-slate-950 p-4 justify-end gap-2 border-t border-slate-700 absolute bottom-0"
            ):
                ui.button("Cancel", on_click=self.dialog.close).props("flat")
                ui.button("Save System", on_click=self.save).classes("bg-green-600")

        self.dialog.open()

    async def run_extraction(self):
        if not self.rules.strip():
            ui.notify("Please enter Rules text first.", type="warning")
            return

        self.gen_btn.disable()
        self.status_label.set_text("Initializing Extraction...")

        await asyncio.to_thread(self._execute_extraction)

        self.gen_btn.enable()

    def _execute_extraction(self):
        connector = self.orchestrator._get_llm_connector()
        service = RulesGenerator(connector, status_callback=self._update_status)

        try:
            ruleset = service.generate_ruleset(self.rules)
            self.ruleset_json = ruleset.model_dump_json(indent=2)
            self._update_status("Extraction Complete!")
        except Exception as e:
            logger.warn(f"Rules extraction failed: {e}")
            self._update_status(f"Error: {str(e)}")

    def _update_status(self, msg):
        self.status_label.set_text(msg)

    def save(self):
        if not self.name or not self.content:
            ui.notify("Name and System Instruction are required.", type="negative")
            return

        # Prepare Manifest
        manifest_str = "{}"
        if self.ruleset_json.strip():
            try:
                # Validate JSON
                data = json.loads(self.ruleset_json)
                # Wrap in 'ruleset' key if not already
                if "ruleset" not in data:
                    final_data = {"ruleset": data}
                else:
                    final_data = data
                manifest_str = json.dumps(final_data)
            except json.JSONDecodeError:
                ui.notify("Invalid JSON in Mechanics field.", type="negative")
                return

        if self.prompt:
            # Update
            self.prompt.name = self.name
            self.prompt.content = self.content
            self.prompt.rules_document = self.rules
            self.prompt.template_manifest = manifest_str
            self.db.prompts.update(self.prompt)
            ui.notify(f"Updated '{self.name}'")
        else:
            # Create
            self.db.prompts.create(self.name, self.content, self.rules, manifest_str)
            ui.notify(f"Created '{self.name}'")

        if self.on_save:
            self.on_save()
        self.dialog.close()
