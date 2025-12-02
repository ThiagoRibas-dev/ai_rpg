from nicegui import ui
from app.gui.theme import Theme
import asyncio
from app.setup.world_gen_service import WorldGenService
from app.models.stat_block import StatBlockTemplate
import json

class SetupWizard:
    def __init__(self, db_manager, orchestrator, prompt, on_complete):
        self.db = db_manager
        self.orchestrator = orchestrator
        self.prompt = prompt
        self.on_complete = on_complete
        
        self.dialog = ui.dialog()
        self.stepper = None
        
        # State
        self.input_world = "A cyberpunk city where it always rains."
        self.input_char = "A washed-up detective with a robotic arm."
        self.extracted_world = None
        self.extracted_char = None
        self.generated_opening = ""
        self.is_generating = False

    def open(self):
        with self.dialog, ui.card().classes('w-[800px] h-[600px] bg-slate-900 border border-slate-700'):
            with ui.row().classes('w-full items-center justify-between'):
                ui.label(f"New Game: {self.prompt.name}").classes('text-xl font-bold text-white')
                ui.button(icon='close', on_click=self.dialog.close).props('flat dense round')

            # ✅ FIX: Initialize stepper and enter its context
            self.stepper = ui.stepper().classes('w-full h-full bg-transparent')
            
            with self.stepper:
                # --- STEP 1: CONCEPT ---
                with ui.step('Concept'):
                    with ui.column().classes('w-full gap-4'):
                        ui.label("Describe the World").classes(Theme.text_secondary)
                        ui.textarea(value=self.input_world).bind_value(self, 'input_world').classes('w-full').props('rows=3')
                        
                        ui.label("Describe your Character").classes(Theme.text_secondary)
                        ui.textarea(value=self.input_char).bind_value(self, 'input_char').classes('w-full').props('rows=3')
                        
                        with ui.stepper_navigation():
                            ui.button('Next', on_click=self.run_generation).classes('bg-blue-600')

                # --- STEP 2: GENERATION (Spinner) ---
                with ui.step('Generation'):
                    with ui.column().classes('w-full h-full items-center justify-center gap-4'):
                        self.spinner = ui.spinner(size='lg').classes('text-blue-500')
                        self.status_label = ui.label("Initializing...").classes('text-lg animate-pulse')
                        
                        with ui.stepper_navigation():
                            # Hidden navigation, moved programmatically
                            self.btn_review = ui.button('Review', on_click=self.stepper.next).classes('hidden')

                # --- STEP 3: REVIEW ---
                with ui.step('Review'):
                    with ui.scroll_area().classes('h-64 w-full border border-slate-700 p-2 rounded'):
                        self.review_container = ui.column().classes('w-full')
                    
                    with ui.stepper_navigation():
                        ui.button('Start Game', on_click=self.finish).classes('bg-green-600')
                        ui.button('Back', on_click=self.stepper.previous).props('flat')

        self.dialog.open()

    async def run_generation(self):
        self.stepper.next() # Move to spinner
        self.is_generating = True
        
        # Run in background thread so UI doesn't freeze
        await asyncio.to_thread(self._execute_llm_pipeline)
        
        # Render review data
        self._render_review()
        self.btn_review.classes(remove='hidden') # Allow next
        self.stepper.next() # Move to review

    def _execute_llm_pipeline(self):
        connector = self.orchestrator._get_llm_connector()
        service = WorldGenService(connector, status_callback=self._update_status)
        
        # 1. Parse Template (Stub logic for now)
        stat_template = None 
        if self.prompt.template_manifest and self.prompt.template_manifest != "{}":
            try:
                data = json.loads(self.prompt.template_manifest)
                if "stat_template" in data:
                    stat_template = StatBlockTemplate(**data["stat_template"])
            except:
                pass
        
        if not stat_template:
            from app.setup.scaffolding import _get_default_scaffolding
            _, stat_template = _get_default_scaffolding()

        # 2. Extract
        self._update_status("Building World...")
        self.extracted_world = service.extract_world_data(self.input_world)
        
        self._update_status("Creating Character...")
        self.extracted_char = service.extract_character_data(self.input_char, stat_template)
        
        self._update_status("Writing Intro...")
        self.generated_opening = service.generate_opening_crawl(
            self.extracted_char, self.extracted_world, self.input_world
        )

    def _update_status(self, msg):
        self.status_label.set_text(msg)

    def _render_review(self):
        self.review_container.clear()
        with self.review_container:
            ui.label("Name").classes('font-bold text-xs uppercase text-gray-500')
            ui.input().bind_value(self.extracted_char, 'name').classes('w-full mb-2')
            
            ui.label("Opening Crawl").classes('font-bold text-xs uppercase text-gray-500')
            ui.textarea().bind_value(self, 'generated_opening').classes('w-full').props('rows=4')

    def finish(self):
        from datetime import datetime
        from app.setup.scaffolding import inject_setup_scaffolding
        
        name = f"{datetime.now().strftime('%H-%M')} - {self.extracted_char.name}"
        
        # Create Session in DB
        self.orchestrator.new_session(self.prompt.content, self.prompt.template_manifest)
        self.orchestrator.session.add_message("assistant", self.generated_opening)
        
        self.orchestrator.save_game(name, self.prompt.id)
        sess_id = self.orchestrator.session.id
        
        # Inject Scaffolding
        inject_setup_scaffolding(sess_id, self.prompt.template_manifest, self.db)
        
        # TODO: Apply Character Extraction Data to Entity
        # This requires manually mapping the 'extracted_char' fields to the entity update logic
        # For MVP, we skip it to get the game running, but the character sheet will be default.
        
        ui.notify("Game Created!")
        self.dialog.close()
        if self.on_complete:
            self.on_complete()