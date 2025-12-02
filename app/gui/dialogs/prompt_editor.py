
from nicegui import ui
import json
import asyncio
from app.models.prompt import Prompt
from app.setup.template_generation_service import TemplateGenerationService

class PromptEditorDialog:
    def __init__(self, db_manager, orchestrator, prompt: Prompt = None, on_save=None):
        self.db = db_manager
        self.orchestrator = orchestrator
        self.prompt = prompt
        self.on_save = on_save
        self.dialog = ui.dialog()
        
        # State
        self.name = prompt.name if prompt else "New System"
        self.content = prompt.content if prompt else "You are a Game Master for..."
        self.rules = prompt.rules_document if prompt else ""
        self.template_json = prompt.template_manifest if prompt else "{}"
        
        # UI Refs
        self.status_label = None
        self.gen_btn = None

    def open(self):
        with self.dialog, ui.card().classes('w-[900px] h-[800px] bg-slate-900 border border-slate-700 p-0'):
            
            # Header
            with ui.row().classes('w-full bg-slate-950 p-4 justify-between items-center border-b border-slate-700'):
                title = "Edit Prompt" if self.prompt else "Create Prompt"
                ui.label(title).classes('text-xl font-bold text-white')
                ui.button(icon='close', on_click=self.dialog.close).props('flat dense round')

            # Body
            with ui.row().classes('w-full h-full gap-0'):
                
                # LEFT COLUMN: Inputs
                with ui.column().classes('w-1/2 h-full p-4 border-r border-slate-800 scroll-y'):
                    ui.input(label="System Name").bind_value(self, 'name').classes('w-full mb-2')
                    
                    ui.label("System Instruction").classes('text-xs font-bold text-gray-500 uppercase mt-2')
                    ui.textarea().bind_value(self, 'content').classes('w-full text-sm').props('rows=6 outlined')
                    
                    ui.label("Rules Document").classes('text-xs font-bold text-gray-500 uppercase mt-4')
                    ui.label("Paste raw text rules here for extraction.").classes('text-xs text-gray-600 italic')
                    ui.textarea().bind_value(self, 'rules').classes('w-full flex-grow text-sm').props('rows=10 outlined')

                # RIGHT COLUMN: Template Generation
                with ui.column().classes('w-1/2 h-full p-4 flex flex-col'):
                    ui.label("Stat Template (JSON)").classes('text-xs font-bold text-gray-500 uppercase')
                    
                    # Toolbar
                    with ui.row().classes('w-full items-center gap-2 mb-2'):
                        self.gen_btn = ui.button("Generate from Rules", on_click=self.run_generation) \
                            .classes('bg-purple-700 text-xs').props('icon=auto_awesome')
                        self.status_label = ui.label("").classes('text-xs text-green-400')

                    # Editor
                    ui.textarea().bind_value(self, 'template_json').classes('w-full h-full font-mono text-xs') \
                        .props('outlined input-class="h-full"')

            # Footer
            with ui.row().classes('w-full bg-slate-950 p-4 justify-end gap-2 border-t border-slate-700 absolute bottom-0'):
                ui.button("Cancel", on_click=self.dialog.close).props('flat')
                ui.button("Save System", on_click=self.save).classes('bg-green-600')

        self.dialog.open()

    async def run_generation(self):
        if not self.rules.strip():
            ui.notify("Please enter Rules text first.", type='warning')
            return

        self.gen_btn.disable()
        self.status_label.set_text("Initializing...")
        
        # Run extraction in background
        await asyncio.to_thread(self._execute_generation)
        
        self.gen_btn.enable()

    def _execute_generation(self):
        connector = self.orchestrator._get_llm_connector()
        service = TemplateGenerationService(connector, self.rules, status_callback=self._update_status)
        
        try:
            ruleset, template = service.generate_template()
            
            # Combine into manifest
            manifest = {
                "ruleset": ruleset.model_dump(),
                "stat_template": template.model_dump()
            }
            
            self.template_json = json.dumps(manifest, indent=2)
            self._update_status("Generation Complete!")
            
        except Exception as e:
            self._update_status(f"Error: {str(e)}")

    def _update_status(self, msg):
        self.status_label.set_text(msg)

    def save(self):
        if not self.name or not self.content:
            ui.notify("Name and System Instruction are required.", type='negative')
            return

        # Validate JSON
        try:
            json.loads(self.template_json)
        except:
            ui.notify("Invalid JSON in Template.", type='negative')
            return

        if self.prompt:
            # Update
            self.prompt.name = self.name
            self.prompt.content = self.content
            self.prompt.rules_document = self.rules
            self.prompt.template_manifest = self.template_json
            self.db.prompts.update(self.prompt)
            ui.notify(f"Updated '{self.name}'")
        else:
            # Create
            self.db.prompts.create(
                self.name, self.content, self.rules, self.template_json
            )
            ui.notify(f"Created '{self.name}'")

        if self.on_save: self.on_save()
        self.dialog.close()
