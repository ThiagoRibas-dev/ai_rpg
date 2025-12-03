from nicegui import ui
import asyncio
import logging
from app.setup.world_gen_service import WorldGenService
from app.setup.sheet_generator import SheetGenerator
from app.services.game_setup_service import GameSetupService
from app.tools.schemas import MemoryUpsert

logger = logging.getLogger(__name__)


class SetupWizard:
    def __init__(self, db_manager, orchestrator, prompt, on_complete):
        self.db = db_manager
        self.orchestrator = orchestrator
        self.prompt = prompt
        self.on_complete = on_complete

        self.dialog = ui.dialog()
        self.stepper = None

        # Inputs
        self.input_world = "A dark fantasy world where the sun has died."
        self.input_char = "A grizzled lantern-bearer."

        # Outputs
        self.generated_spec = None  # CharacterSheetSpec
        self.generated_values = None  # Dict
        self.extracted_world = None  # WorldExtraction
        self.generated_opening = ""

        self.is_generating = False

        # Editor State
        self.edit_lore_text = ""

    def open(self):
        with (
            self.dialog,
            ui.card().classes(
                "w-[1000px] h-[800px] bg-slate-900 border border-slate-700"
            ),
        ):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(f"New Game: {self.prompt.name}").classes(
                    "text-xl font-bold text-white"
                )
                ui.button(icon="close", on_click=self.dialog.close).props(
                    "flat dense round"
                )

            self.stepper = ui.stepper().classes("w-full h-full bg-transparent")

            with self.stepper:
                # --- STEP 1: CONCEPT ---
                with ui.step("Concept"):
                    with ui.column().classes("w-full gap-4"):
                        ui.label("The System Rules").classes(
                            "text-sm font-bold text-gray-400"
                        )
                        ui.markdown(
                            f"Using rules from: **{self.prompt.name}**"
                        ).classes("text-xs text-gray-500")

                        with ui.row().classes("w-full gap-4"):
                            with ui.column().classes("flex-grow"):
                                ui.label("The World").classes(
                                    "text-lg font-bold text-amber-500"
                                )
                                ui.textarea(value=self.input_world).bind_value(
                                    self, "input_world"
                                ).classes("w-full").props("rows=6 outlined")

                            with ui.column().classes("flex-grow"):
                                ui.label("The Protagonist").classes(
                                    "text-lg font-bold text-amber-500"
                                )
                                ui.textarea(value=self.input_char).bind_value(
                                    self, "input_char"
                                ).classes("w-full").props("rows=6 outlined")

                        with ui.stepper_navigation():
                            ui.button("Generate", on_click=self.run_generation).classes(
                                "bg-blue-600"
                            )

                # --- STEP 2: GENERATION ---
                with ui.step("Generation"):
                    with ui.column().classes(
                        "w-full h-full items-center justify-center gap-4"
                    ):
                        self.spinner = ui.spinner(size="lg").classes("text-blue-500")
                        self.status_label = ui.label("Initializing...").classes(
                            "text-lg animate-pulse"
                        )

                        with ui.stepper_navigation():
                            self.btn_review = ui.button(
                                "Review Data", on_click=self.stepper.next
                            ).classes("hidden")

                # --- STEP 3: REVIEW & EDIT ---
                with ui.step("Review"):
                    self.review_container = ui.column().classes("w-full h-[550px]")

                    with ui.stepper_navigation():
                        ui.button("Start Game", on_click=self.finish).classes(
                            "bg-green-600"
                        )
                        ui.button("Back", on_click=self.stepper.previous).props("flat")

        self.dialog.open()

    async def run_generation(self):
        self.stepper.next()
        self.is_generating = True

        # Run in background
        await asyncio.to_thread(self._execute_pipeline)

        self._prepare_review_data()
        self._render_review()
        self.btn_review.classes(remove="hidden")
        self.stepper.next()

    def _execute_pipeline(self):
        connector = self.orchestrator._get_llm_connector()

        # 1. World Gen
        self._update_status("Building World...")
        world_service = WorldGenService(connector)
        self.extracted_world = world_service.extract_world_data(self.input_world)

        # 2. Sheet Architecture (The "Pass 1")
        self._update_status("Architecting Character Sheet...")
        sheet_gen = SheetGenerator(connector)
        # We use the prompt's rules text
        self.generated_spec = sheet_gen.generate_structure(
            self.prompt.rules_document, self.input_char
        )

        # 3. Sheet Population (The "Pass 2")
        self._update_status("Populating Character Data...")
        self.generated_values = sheet_gen.populate_sheet(
            self.generated_spec, self.input_char
        )

        # 4. Opening Crawl
        self._update_status("Writing Intro...")

        # Create a dummy char object for the crawl generator since it expects the old schema
        class DummyChar:
            name = self.generated_values.get("identity", {}).get("name", "Player")

        self.generated_opening = world_service.generate_opening_crawl(
            DummyChar(), self.extracted_world, self.input_world
        )

        self._update_status("Done!")

    def _update_status(self, msg):
        self.status_label.set_text(msg)

    def _prepare_review_data(self):
        if self.extracted_world:
            self.edit_lore_text = "\n".join(
                [m.content for m in self.extracted_world.lore]
            )

    def _render_review(self):
        self.review_container.clear()
        with self.review_container:
            with ui.tabs().classes("w-full text-gray-400") as tabs:
                t_char = ui.tab("Character Sheet")
                t_world = ui.tab("World Info")
                t_intro = ui.tab("Opening")

            with ui.tab_panels(tabs, value=t_char).classes(
                "w-full flex-grow bg-slate-800 p-2 rounded scroll-y"
            ):
                # --- DYNAMIC CHARACTER SHEET REVIEW ---
                with ui.tab_panel(t_char):
                    self._render_dynamic_sheet_form()

                # --- WORLD TAB ---
                with ui.tab_panel(t_world):
                    with ui.scroll_area().classes("h-full"):
                        ui.label("Starting Location").classes(
                            "text-xs font-bold text-gray-500 uppercase"
                        )
                        ui.input(label="Location Name").bind_value(
                            self.extracted_world.starting_location, "name_display"
                        ).classes("w-full mb-2")
                        ui.textarea(label="Description").bind_value(
                            self.extracted_world.starting_location, "description_visual"
                        ).classes("w-full mb-4").props("rows=3")

                        ui.label("Lore & Facts (One fact per line)").classes(
                            "text-xs font-bold text-gray-500 uppercase"
                        )
                        ui.textarea().bind_value(self, "edit_lore_text").classes(
                            "w-full"
                        ).props("rows=8")

                # --- INTRO TAB ---
                with ui.tab_panel(t_intro):
                    ui.label("Opening Crawl").classes(
                        "text-xs font-bold text-gray-500 uppercase"
                    )
                    ui.textarea().bind_value(self, "generated_opening").classes(
                        "w-full h-full"
                    ).props("rows=12")

    def _render_dynamic_sheet_form(self):
        """
        Renders inputs based on the generated Schema.
        Allows user to edit self.generated_values.
        """
        if not self.generated_spec or not self.generated_values:
            ui.label("No data generated.")
            return

        # Iterate categories in the spec
        spec_dict = self.generated_spec.model_dump()

        # Categories to show in order
        cats = [
            "identity",
            "attributes",
            "resources",
            "skills",
            "inventory",
            "features",
        ]

        for cat_key in cats:
            if cat_key not in spec_dict:
                continue

            category = spec_dict[cat_key]
            fields = category.get("fields", {})
            if not fields:
                continue

            # Ensure value dict exists
            if cat_key not in self.generated_values:
                self.generated_values[cat_key] = {}

            ui.label(cat_key.title()).classes(
                "text-lg font-bold text-amber-500 mt-2 border-b border-slate-700 w-full"
            )

            with ui.grid(columns=2).classes("w-full gap-4 p-2"):
                for field_key, field_def in fields.items():
                    self._render_field_input(cat_key, field_key, field_def)

    def _render_field_input(self, cat, key, definition):
        """Render a single input based on widget type."""
        container_type = definition.get("container_type", "atom")
        display = definition.get("display", {})
        label = display.get("label", key)
        widget = display.get("widget", "text")

        # Access Value Reference
        cat_data = self.generated_values[cat]

        if container_type == "atom":
            if widget == "number" or widget == "die":
                # Check if value is int or str
                val = cat_data.get(key, 0)
                if isinstance(val, int) or (isinstance(val, str) and val.isdigit()):
                    ui.number(
                        label=label,
                        value=int(val),
                        on_change=lambda e, c=cat_data, k=key: c.update(
                            {k: int(e.value)}
                        ),
                    ).classes("w-full")
                else:
                    ui.input(
                        label=label,
                        value=str(val),
                        on_change=lambda e, c=cat_data, k=key: c.update({k: e.value}),
                    ).classes("w-full")
            else:
                ui.input(label=label, value=str(cat_data.get(key, ""))).bind_value(
                    cat_data, key
                ).classes("w-full")

        elif container_type == "molecule":
            # For pools, we edit Current and Max
            if widget == "pool":
                if key not in cat_data:
                    cat_data[key] = {"current": 0, "max": 0}
                with ui.row().classes(
                    "items-center gap-2 border border-slate-700 p-2 rounded"
                ):
                    ui.label(label).classes("text-xs font-bold w-20")
                    ui.number(
                        label="Cur", value=cat_data[key].get("current", 0)
                    ).bind_value(cat_data[key], "current").classes("w-20")
                    ui.label("/")
                    ui.number(
                        label="Max", value=cat_data[key].get("max", 0)
                    ).bind_value(cat_data[key], "max").classes("w-20")

    def finish(self):
        # 1. Parse Lore back
        lore_lines = [
            line.strip() for line in self.edit_lore_text.split("\n") if line.strip()
        ]
        self.extracted_world.lore = [
            MemoryUpsert(kind="lore", content=line, priority=3, tags=["world_gen"])
            for line in lore_lines
        ]

        # 2. Call Service
        service = GameSetupService(self.db)

        try:
            game_session = service.create_game(
                prompt=self.prompt,
                char_data=None,  # Legacy ignored
                world_data=self.extracted_world,
                opening_crawl=self.generated_opening,
                sheet_spec=self.generated_spec,
                sheet_values=self.generated_values,
            )

            self.orchestrator.load_game(game_session.id)
            ui.notify("Game Created Successfully!")
            self.dialog.close()
            if self.on_complete:
                self.on_complete()

        except Exception as e:
            ui.notify(f"Creation Failed: {str(e)}", type="negative")
            logger.error(f"Creation failed: {e}", exc_info=True)
