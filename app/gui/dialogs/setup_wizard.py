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
        self.dialog.props("persistent")
        self.stepper = None

        # Inputs
        self.input_world = ""
        self.input_char = ""

        # Outputs
        self.generated_spec = None
        self.generated_values = None
        self.extracted_world = None
        self.generated_opening = ""

        self.is_generating = False

        # UI State for Lore (List of dicts for binding)
        # Structure: [{"content": "The king is dead", "tags_str": "politics, king"}]
        self.lore_ui_items = []

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
                                ui.textarea(
                                    value=self.input_world,
                                    placeholder="A dark fantasy world where the sun has died.",
                                ).bind_value(self, "input_world").classes(
                                    "w-full"
                                ).props("rows=6 outlined")

                            with ui.column().classes("flex-grow"):
                                ui.label("The Protagonist").classes(
                                    "text-lg font-bold text-amber-500"
                                )
                                ui.textarea(
                                    value=self.input_char,
                                    placeholder="A grizzled lantern-bearer.",
                                ).bind_value(self, "input_char").classes(
                                    "w-full"
                                ).props("rows=6 outlined")

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

        # 2. Sheet Architecture
        self._update_status("Architecting Character Sheet...")
        sheet_gen = SheetGenerator(connector)
        self.generated_spec = sheet_gen.generate_structure(
            self.prompt.rules_document, self.input_char
        )

        # 3. Sheet Population (Now passing rules_text)
        self._update_status("Populating Character Data...")
        self.generated_values = sheet_gen.populate_sheet(
            self.generated_spec, self.input_char, rules_text=self.prompt.rules_document
        )

        # 4. Opening Crawl
        self._update_status("Writing Intro...")

        class DummyChar:
            name = self.generated_values.get("identity", {}).get("name", "Player")

        self.generated_opening = world_service.generate_opening_crawl(
            DummyChar(), self.extracted_world, self.input_world
        )

        self._update_status("Done!")

    def _update_status(self, msg):
        self.status_label.set_text(msg)

    def _prepare_review_data(self):
        """Convert WorldExtraction objects into bindable UI dictionaries."""
        if self.extracted_world:
            self.lore_ui_items = []
            for lore in self.extracted_world.lore:
                # Convert list of tags to comma-string for easy editing
                tags_str = ", ".join(lore.tags) if lore.tags else "world_gen"
                self.lore_ui_items.append(
                    {"content": lore.content, "tags_str": tags_str}
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
                # --- CHARACTER SHEET ---
                with ui.tab_panel(t_char):
                    self._render_dynamic_sheet_form()

                # --- WORLD TAB ---
                with ui.tab_panel(t_world):
                    with ui.scroll_area().classes("h-full pr-4"):
                        ui.label("Starting Location").classes(
                            "text-xs font-bold text-gray-500 uppercase"
                        )
                        ui.input(label="Location Name").bind_value(
                            self.extracted_world.starting_location, "name"
                        ).classes("w-full mb-2")

                        ui.textarea(label="Description").bind_value(
                            self.extracted_world.starting_location, "description_visual"
                        ).classes("w-full mb-4").props("rows=3")

                        # --- LORE EDITOR (List View) ---
                        with ui.row().classes("w-full justify-between items-center"):
                            ui.label("World Lore & Secrets").classes(
                                "text-xs font-bold text-gray-500 uppercase"
                            )
                            ui.button(icon="add", on_click=self._add_lore_row).props(
                                "flat dense round size=sm"
                            )

                        # Render the list of lore items
                        self.lore_list_container = ui.column().classes("w-full gap-2")
                        with self.lore_list_container:
                            self._render_lore_list()

                # --- INTRO TAB ---
                with ui.tab_panel(t_intro):
                    ui.label("Opening Crawl").classes(
                        "text-xs font-bold text-gray-500 uppercase"
                    )
                    ui.textarea().bind_value(self, "generated_opening").classes(
                        "w-full h-full"
                    ).props("rows=12")

    def _render_lore_list(self):
        self.lore_list_container.clear()
        with self.lore_list_container:
            for index, item in enumerate(self.lore_ui_items):
                with ui.row().classes(
                    "w-full items-start gap-2 bg-slate-900 p-2 rounded"
                ):
                    # Content (Wide)
                    ui.textarea(label="Fact/Event").bind_value(item, "content").classes(
                        "flex-grow"
                    ).props("rows=2 dense")

                    # Tags (Narrow)
                    ui.input(label="Tags").bind_value(item, "tags_str").classes(
                        "w-1/4"
                    ).props("dense")

                    # Delete Button
                    ui.button(
                        icon="delete", on_click=lambda i=index: self._delete_lore_row(i)
                    ).props("flat dense color=red round").classes("mt-2")

    def _add_lore_row(self):
        self.lore_ui_items.append({"content": "", "tags_str": "world_gen"})
        self._render_lore_list()

    def _delete_lore_row(self, index):
        if 0 <= index < len(self.lore_ui_items):
            self.lore_ui_items.pop(index)
            self._render_lore_list()

    def _render_dynamic_sheet_form(self):
        if not self.generated_spec or not self.generated_values:
            ui.label("No data generated.")
            return

        spec_dict = self.generated_spec.model_dump()
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

            if cat_key not in self.generated_values or not isinstance(
                self.generated_values[cat_key], dict
            ):
                self.generated_values[cat_key] = {}

            ui.label(cat_key.title()).classes(
                "text-lg font-bold text-amber-500 mt-2 border-b border-slate-700 w-full"
            )

            with ui.grid(columns=2).classes("w-full gap-4 p-2"):
                for field_key, field_def in fields.items():
                    self._render_field_input(cat_key, field_key, field_def)

    def _render_field_input(self, cat, key, definition):
        container_type = definition.get("container_type", "atom")
        display = definition.get("display", {})
        label = display.get("label", key)
        widget = display.get("widget", "text")
        cat_data = self.generated_values[cat]

        if container_type == "atom":
            if widget == "number" or widget == "die":
                val = cat_data.get(key, 0)
                is_num = isinstance(val, int)
                is_digit = isinstance(val, str) and val.isdigit()

                if is_num or is_digit:
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
                        value=str(val) if val is not None else "",
                        on_change=lambda e, c=cat_data, k=key: c.update({k: e.value}),
                    ).classes("w-full")
            else:
                ui.input(label=label, value=str(cat_data.get(key, ""))).bind_value(
                    cat_data, key
                ).classes("w-full")

        elif container_type == "molecule":
            raw_val = cat_data.get(key)
            if raw_val is not None and not isinstance(raw_val, dict):
                cat_data[key] = {"current": raw_val, "max": raw_val}

            if key not in cat_data or not isinstance(cat_data[key], dict):
                cat_data[key] = {"current": 0, "max": 0}

            if widget == "pool":
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
        # Reconstruct MemoryUpsert objects from the UI List, preserving tags
        final_lore = []
        for item in self.lore_ui_items:
            content = item.get("content", "").strip()
            if not content:
                continue

            # Split tags string back into list
            tags_str = item.get("tags_str", "")
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            if "world_gen" not in tags:
                tags.append("world_gen")

            final_lore.append(
                MemoryUpsert(kind="lore", content=content, priority=3, tags=tags)
            )

        self.extracted_world.lore = final_lore

        service = GameSetupService(self.db)

        try:
            game_session = service.create_game(
                prompt=self.prompt,
                char_data=None,
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
