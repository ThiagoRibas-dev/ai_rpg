from nicegui import ui
import asyncio
import time
from app.models.prompt import Prompt
from app.setup.manifest_extractor import ManifestExtractor
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

        # State: Manifest
        self.manifest_json = "{}"
        if prompt and prompt.template_manifest:
            self.manifest_json = prompt.template_manifest

        self.status_label = None
        self.gen_btn = None

        # Extraction State
        self.extraction_start_time = None
        self.current_status_msg = ""
        self.status_timer = None

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
                title = "Edit Prompt" if self.prompt else "Create New Game Config"
                ui.label(title).classes("text-xl font-bold text-white")
                ui.button(icon="close", on_click=self.dialog.close).props(
                    "flat dense round"
                )

            with ui.row().classes("w-full h-full gap-0"):
                # Left: Text (Narrative & Custom Rules)
                with ui.column().classes(
                    "w-1/2 h-full p-4 border-r border-slate-800 scroll-y gap-4"
                ):
                    ui.input(label="Configuration Name").bind_value(
                        self, "name"
                    ).classes("w-full").props(
                        "placeholder='e.g. Cyberpunk Noir Campaign'"
                    )

                    ui.label("System Instruction (The Narrator)").classes(
                        "text-xs font-bold text-gray-500 uppercase mt-2"
                    )
                    ui.textarea(placeholder="You are the GM...").bind_value(
                        self, "content"
                    ).classes("w-full").props("rows=4 outlined")

                    ui.label("Rules Document (Reference)").classes(
                        "text-xs font-bold text-gray-500 uppercase mt-2"
                    )
                    ui.textarea(
                        placeholder="Paste raw rules text here OR load a system on the right..."
                    ).bind_value(self, "rules").classes("w-full flex-grow").props(
                        "rows=10 outlined"
                    )

                # Right: System Definition (The Mechanics)
                with ui.column().classes("w-1/2 h-full p-4 flex flex-col gap-2"):
                    ui.label("Game System Configuration").classes(
                        "text-xs font-bold text-gray-500 uppercase"
                    )

                    # --- System Loader ---
                    with ui.row().classes(
                        "w-full items-center gap-2 bg-slate-800 p-2 rounded"
                    ):
                        ui.icon("settings_system_daydream").classes("text-gray-400")

                        # Load manifests for dropdown
                        manifests = self.db.manifests.get_all()
                        options = {m["id"]: m["name"] for m in manifests}

                        ui.select(
                            options,
                            label="Load Pre-Built System",
                            on_change=self._load_system_template,
                        ).classes("flex-grow").props("dense outlined")

                    ui.label("System Manifest (JSON)").classes(
                        "text-xs font-bold text-gray-500 uppercase mt-2"
                    )
                    ui.label("Defines stats, engine, and tools.").classes(
                        "text-xs text-gray-600 italic"
                    )

                    # Controls
                    with ui.row().classes("w-full items-center gap-2 mb-2"):
                        self.gen_btn = (
                            ui.button(
                                "Extract from Rules Text", on_click=self.run_extraction
                            )
                            .classes("bg-purple-700 text-xs")
                            .props("icon=auto_awesome")
                        )
                        self.status_label = ui.label("").classes(
                            "text-xs text-green-400 font-mono"
                        )

                    # JSON Editor
                    ui.textarea().bind_value(self, "manifest_json").classes(
                        "w-full h-full font-mono text-xs"
                    ).props('outlined input-class="h-full font-mono text-xs"')

            with ui.row().classes(
                "w-full bg-slate-950 p-4 justify-end gap-2 border-t border-slate-700 absolute bottom-0"
            ):
                ui.button("Cancel", on_click=self.dialog.close).props("flat")
                ui.button("Save Configuration", on_click=self.save).classes(
                    "bg-green-600"
                )

        self.dialog.open()

    def _load_system_template(self, e):
        """Loads a selected manifest into the JSON editor."""
        manifest_id = e.value
        manifest = self.db.manifests.get_by_id(manifest_id)

        if manifest:
            self.manifest_json = manifest.to_json()

            # If rules text is empty, add a placeholder so the user knows rules are loaded
            if not self.rules.strip():
                self.rules = f"Using System: {manifest.name}\n\nRefer to the System Manifest for engine mechanics and valid stat paths."

            ui.notify(f"Loaded {manifest.name}")

    async def run_extraction(self):
        if not self.rules.strip():
            ui.notify("Please enter Rules text on the left first.", type="warning")
            return

        self.gen_btn.disable()
        self.extraction_start_time = time.time()
        self.current_status_msg = "Initializing..."

        # Start UI timer to update label with elapsed time
        self.status_timer = ui.timer(0.1, self._refresh_status_ui)

        await asyncio.to_thread(self._execute_extraction)

        # Cleanup
        if self.status_timer:
            self.status_timer.cancel()
            self.status_timer = None

        elapsed = time.time() - self.extraction_start_time
        self.status_label.set_text(f"Complete! ({elapsed:.1f}s)")
        self.gen_btn.enable()

    def _refresh_status_ui(self):
        if self.extraction_start_time:
            elapsed = time.time() - self.extraction_start_time
            self.status_label.set_text(f"{self.current_status_msg} ({elapsed:.1f}s)")

    def _execute_extraction(self):
        connector = self.orchestrator._get_llm_connector()
        extractor = ManifestExtractor(connector, status_callback=self._update_status)
        try:
            # 1. Run Pipeline
            manifest = extractor.extract(self.rules)
            
            # 2. Update Name if empty
            if not self.name and manifest.name:
                self.name = manifest.name

            # 3. Serialize to UI
            self.manifest_json = manifest.to_json(indent=2)
            
            self._update_status("Extraction Complete!")
        except Exception as e:
            logger.error(f"Rules extraction failed: {e}", exc_info=True)
            self._update_status(f"Error: {str(e)}")

    def _update_status(self, msg):
        self.current_status_msg = msg

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
