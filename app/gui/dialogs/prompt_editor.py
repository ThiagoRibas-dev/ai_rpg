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
        self.dialog.props("persistent")

        self.name = prompt.name if prompt else ""
        self.content = prompt.content if prompt else ""
        self.rules = prompt.rules_document if prompt else ""

        # State: Manifest (Ruleset + Base Rules)
        self.manifest_json = "{}"
        if prompt and prompt.template_manifest:
            self.manifest_json = prompt.template_manifest

        self.status_label = None
        self.gen_btn = None

    def open(self):
        with (
            self.dialog,
            ui.card().classes(
                "w-[1200px] h-[800px] bg-slate-900 border border-slate-700 p-0"
            ),
        ):
            with ui.row().classes(
                "w-full bg-slate-950 p-4 justify-between items-center border-b border-slate-700"
            ):
                title = "Edit Prompt" if self.prompt else "Create Prompt"
                ui.label(title).classes("text-xl font-bold text-white")
                ui.button(icon="close", on_click=self.dialog.close).props(
                    "flat dense round"
                )

            with ui.row().classes("w-full h-full gap-0"):
                # Left: Text
                with ui.column().classes(
                    "w-1/2 h-full p-4 border-r border-slate-800 scroll-y gap-4"
                ):
                    ui.input(label="System Name").bind_value(self, "name").classes(
                        "w-full"
                    )
                    ui.label("System Instruction").classes(
                        "text-xs font-bold text-gray-500 uppercase mt-2"
                    )
                    ui.textarea(placeholder="You are the GM...").bind_value(
                        self, "content"
                    ).classes("w-full").props("rows=4 outlined")
                    ui.label("Rules Document").classes(
                        "text-xs font-bold text-gray-500 uppercase mt-2"
                    )
                    ui.textarea(placeholder="Paste rules text here...").bind_value(
                        self, "rules"
                    ).classes("w-full flex-grow").props("rows=10 outlined")

                # Right: Extraction JSON
                with ui.column().classes("w-1/2 h-full p-4 flex flex-col"):
                    ui.label("System Manifest (JSON)").classes(
                        "text-xs font-bold text-gray-500 uppercase"
                    )
                    ui.label("Contains Engine Config and Base Rules.").classes(
                        "text-xs text-gray-600 italic"
                    )

                    with ui.row().classes("w-full items-center gap-2 mb-2"):
                        self.gen_btn = (
                            ui.button("Extract Rules", on_click=self.run_extraction)
                            .classes("bg-purple-700 text-xs")
                            .props("icon=auto_awesome")
                        )
                        self.status_label = ui.label("").classes(
                            "text-xs text-green-400"
                        )

                    ui.textarea().bind_value(self, "manifest_json").classes(
                        "w-full h-full font-mono text-xs"
                    ).props('outlined input-class="h-full"')

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
        self.status_label.set_text("Extracting...")
        await asyncio.to_thread(self._execute_extraction)
        self.gen_btn.enable()

    def _execute_extraction(self):
        connector = self.orchestrator._get_llm_connector()
        service = RulesGenerator(connector, status_callback=self._update_status)
        try:
            ruleset, rule_mems, vocabulary = service.generate_ruleset(self.rules)

            # Combine into Manifest (includes vocabulary)
            manifest = {
                "vocabulary": vocabulary.model_dump(),
                "ruleset": ruleset.model_dump(),
                "base_rules": rule_mems,
            }
            self.manifest_json = json.dumps(manifest, indent=2)
            self._update_status("Extraction Complete!")
        except Exception as e:
            logger.warning(f"Rules extraction failed: {e}")
            self._update_status(f"Error: {str(e)}")

    def _update_status(self, msg):
        self.status_label.set_text(msg)

    def save(self):
        if not self.name or not self.content:
            ui.notify("Name and Instruction required.", type="negative")
            return

        if self.prompt:
            self.prompt.name = self.name
            self.prompt.content = self.content
            self.prompt.rules_document = self.rules
            self.prompt.template_manifest = self.manifest_json
            self.db.prompts.update(self.prompt)
        else:
            self.db.prompts.create(
                self.name, self.content, self.rules, self.manifest_json
            )

        if self.on_save:
            self.on_save()
        self.dialog.close()
