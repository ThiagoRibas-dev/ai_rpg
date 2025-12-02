
from nicegui import ui
from app.gui.theme import Theme
import asyncio
from app.setup.world_gen_service import WorldGenService
from app.services.game_setup_service import GameSetupService
from app.models.stat_block import StatBlockTemplate
from app.tools.schemas import MemoryUpsert
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
        
        # Temporary Edit State
        self.edit_inventory_text = ""
        self.edit_lore_text = ""

    def open(self):
        with self.dialog, ui.card().classes('w-[900px] h-[700px] bg-slate-900 border border-slate-700'):
            with ui.row().classes('w-full items-center justify-between'):
                ui.label(f"New Game: {self.prompt.name}").classes('text-xl font-bold text-white')
                ui.button(icon='close', on_click=self.dialog.close).props('flat dense round')

            self.stepper = ui.stepper().classes('w-full h-full bg-transparent')
            
            with self.stepper:
                # --- STEP 1: CONCEPT ---
                with ui.step('Concept'):
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('w-full gap-4'):
                            with ui.column().classes('flex-grow'):
                                ui.label("The World").classes('text-lg font-bold text-amber-500')
                                ui.textarea(value=self.input_world).bind_value(self, 'input_world').classes('w-full').props('rows=6 outlined')
                            
                            with ui.column().classes('flex-grow'):
                                ui.label("The Protagonist").classes('text-lg font-bold text-amber-500')
                                ui.textarea(value=self.input_char).bind_value(self, 'input_char').classes('w-full').props('rows=6 outlined')
                        
                        with ui.stepper_navigation():
                            ui.button('Generate', on_click=self.run_generation).classes('bg-blue-600')

                # --- STEP 2: GENERATION ---
                with ui.step('Generation'):
                    with ui.column().classes('w-full h-full items-center justify-center gap-4'):
                        self.spinner = ui.spinner(size='lg').classes('text-blue-500')
                        self.status_label = ui.label("Initializing...").classes('text-lg animate-pulse')
                        
                        with ui.stepper_navigation():
                            self.btn_review = ui.button('Review Data', on_click=self.stepper.next).classes('hidden')

                # --- STEP 3: REVIEW & EDIT ---
                with ui.step('Review'):
                    self.review_container = ui.column().classes('w-full h-[450px]')
                    
                    with ui.stepper_navigation():
                        ui.button('Start Game', on_click=self.finish).classes('bg-green-600')
                        ui.button('Back', on_click=self.stepper.previous).props('flat')

        self.dialog.open()

    async def run_generation(self):
        self.stepper.next()
        self.is_generating = True
        await asyncio.to_thread(self._execute_llm_pipeline)
        self._prepare_review_data()
        self._render_review()
        self.btn_review.classes(remove='hidden')
        self.stepper.next()

    def _execute_llm_pipeline(self):
        connector = self.orchestrator._get_llm_connector()
        service = WorldGenService(connector, status_callback=self._update_status)
        
        # 1. Parse Template
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

        # 2. Run ETL
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

    def _prepare_review_data(self):
        # Convert lists to text blocks for easier editing
        if self.extracted_char:
            self.edit_inventory_text = "\n".join(self.extracted_char.inventory)
        if self.extracted_world:
            self.edit_lore_text = "\n".join([m.content for m in self.extracted_world.lore])

    def _render_review(self):
        self.review_container.clear()
        with self.review_container:
            with ui.tabs().classes('w-full text-gray-400') as tabs:
                t_char = ui.tab('Character')
                t_world = ui.tab('World')
                t_intro = ui.tab('Opening')

            with ui.tab_panels(tabs, value=t_char).classes('w-full flex-grow bg-slate-800 p-2 rounded'):
                
                # --- CHARACTER TAB ---
                with ui.tab_panel(t_char):
                    with ui.scroll_area().classes('h-full'):
                        ui.label("Identity").classes('text-xs font-bold text-gray-500 uppercase')
                        ui.input(label="Name").bind_value(self.extracted_char, 'name').classes('w-full mb-2')
                        ui.textarea(label="Visual Description").bind_value(self.extracted_char, 'visual_description').classes('w-full mb-4').props('rows=2')
                        
                        ui.label("Stats").classes('text-xs font-bold text-gray-500 uppercase')
                        
                        # Dynamic Stats Grid with Type Checking
                        with ui.grid(columns=3).classes('w-full gap-2 mb-4'):
                            for key, val in self.extracted_char.suggested_stats.items():
                                is_number = isinstance(val, (int, float))
                                
                                if is_number:
                                    # Enforce number input
                                    ui.number(label=key, value=val, on_change=lambda e, k=key: self._update_stat(k, e.value)) \
                                        .classes('w-full')
                                else:
                                    # Allow text
                                    ui.input(label=key, value=str(val), on_change=lambda e, k=key: self._update_stat(k, e.value)) \
                                        .classes('w-full')

                        ui.label("Inventory (One item per line)").classes('text-xs font-bold text-gray-500 uppercase')
                        ui.textarea().bind_value(self, 'edit_inventory_text').classes('w-full').props('rows=5')

                # --- WORLD TAB ---
                with ui.tab_panel(t_world):
                    with ui.scroll_area().classes('h-full'):
                        ui.label("Starting Location").classes('text-xs font-bold text-gray-500 uppercase')
                        ui.input(label="Location Name").bind_value(self.extracted_world.starting_location, 'name_display').classes('w-full mb-2')
                        ui.textarea(label="Description").bind_value(self.extracted_world.starting_location, 'description_visual').classes('w-full mb-4').props('rows=3')
                        
                        ui.label("Lore & Facts (One fact per line)").classes('text-xs font-bold text-gray-500 uppercase')
                        ui.textarea().bind_value(self, 'edit_lore_text').classes('w-full').props('rows=8')

                # --- INTRO TAB ---
                with ui.tab_panel(t_intro):
                    ui.label("Opening Crawl").classes('text-xs font-bold text-gray-500 uppercase')
                    ui.textarea().bind_value(self, 'generated_opening').classes('w-full h-full').props('rows=12')

    def _update_stat(self, key, value):
        # Update model directly. Type conversion handled by ui.number automatically for ints
        self.extracted_char.suggested_stats[key] = value

    def finish(self):
        # 1. Parse Text Areas back into Lists
        # Filter out empty lines
        self.extracted_char.inventory = [
            line.strip() for line in self.edit_inventory_text.split('\n') if line.strip()
        ]
        
        lore_lines = [
            line.strip() for line in self.edit_lore_text.split('\n') if line.strip()
        ]
        
        self.extracted_world.lore = [
            MemoryUpsert(kind="lore", content=line, priority=3, tags=["world_gen"]) 
            for line in lore_lines
        ]

        # 2. Delegate to Service
        service = GameSetupService(self.db)
        
        try:
            game_session = service.create_game(
                prompt=self.prompt,
                char_data=self.extracted_char,
                world_data=self.extracted_world,
                opening_crawl=self.generated_opening
            )
            
            self.orchestrator.load_game(game_session.id)
            ui.notify("Game Created Successfully!")
            self.dialog.close()
            if self.on_complete:
                self.on_complete()
                
        except Exception as e:
            ui.notify(f"Creation Failed: {str(e)}", type='negative')
            print(e)
