from nicegui import ui
from app.gui.theme import Theme
from app.gui.dialogs.setup_wizard import SetupWizard


class PromptListComponent:
    def __init__(self, db_manager, orchestrator, session_list_ref):
        self.db = db_manager
        self.orchestrator = orchestrator
        self.session_list = session_list_ref
        self.container = None

    def render(self):
        self.container = ui.column().classes("w-full gap-2")
        self.refresh()

    def refresh(self):
        self.container.clear()
        prompts = self.db.prompts.get_all()

        with self.container:
            # Header with "Add" button
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("System Prompts").classes("text-sm font-bold text-gray-400")
                ui.button(icon="add", on_click=self.create_prompt).props(
                    "flat dense round"
                )

            if not prompts:
                ui.label("No Prompts Found").classes("text-gray-500 italic text-sm")
                return

            for prompt in prompts:
                with ui.card().classes(
                    "w-full p-2 bg-slate-800 border border-slate-700"
                ):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label(prompt.name).classes("font-bold text-gray-200")

                        # Actions
                        with ui.row().classes("gap-1"):
                            # New Game Button
                            ui.button(
                                icon="play_arrow",
                                on_click=lambda p=prompt: self.start_wizard(p),
                            ).props("flat dense round").classes(
                                "text-green-400"
                            ).tooltip("Start New Game")

                            # Edit (Stub)
                            ui.button(
                                icon="edit",
                                on_click=lambda: ui.notify("Edit Prompt coming soon"),
                            ).props("flat dense round").classes("text-gray-500")

    def create_prompt(self):
        # Quick Stub for creating a basic prompt so you aren't stuck
        self.db.prompts.create("New Prompt", "You are a GM.", "Rules...", "{}")
        self.refresh()
        ui.notify("Created empty prompt")

    def start_wizard(self, prompt):
        # Open the Modal Wizard
        wizard = SetupWizard(
            self.db, self.orchestrator, prompt, on_complete=self.session_list.refresh
        )
        wizard.open()
