
from nicegui import ui
from app.gui.dialogs.setup_wizard import SetupWizard
from app.gui.dialogs.prompt_editor import PromptEditorDialog

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
                ).tooltip("Create New System")

            if not prompts:
                ui.label("No Prompts Found").classes("text-gray-500 italic text-sm")
                return

            for prompt in prompts:
                with ui.card().classes(
                    "w-full p-2 bg-slate-800 border border-slate-700 group"
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

                            # Edit
                            ui.button(
                                icon="edit",
                                on_click=lambda p=prompt: self.edit_prompt(p),
                            ).props("flat dense round").classes("text-gray-500 opacity-50 group-hover:opacity-100")
                            
                            # Delete
                            ui.button(
                                icon="delete",
                                on_click=lambda p=prompt: self.delete_prompt(p),
                            ).props("flat dense round").classes("text-red-500 opacity-0 group-hover:opacity-100")

    def create_prompt(self):
        dialog = PromptEditorDialog(self.db, self.orchestrator, on_save=self.refresh)
        dialog.open()

    def edit_prompt(self, prompt):
        # Fetch full prompt data (get_all is usually lightweight)
        full_prompt = self.db.prompts.get_by_id(prompt.id)
        dialog = PromptEditorDialog(self.db, self.orchestrator, prompt=full_prompt, on_save=self.refresh)
        dialog.open()

    def delete_prompt(self, prompt):
        # Confirm
        with ui.dialog() as dialog, ui.card():
            ui.label(f"Delete System '{prompt.name}'?")
            ui.label("This will NOT delete save files, but they may break.").classes('text-xs text-red-400')
            with ui.row().classes('justify-end'):
                ui.button('Cancel', on_click=dialog.close).props('flat')
                ui.button('Delete', on_click=lambda: self._do_delete(prompt, dialog)).classes('bg-red-600')
        dialog.open()

    def _do_delete(self, prompt, dialog):
        self.db.prompts.delete(prompt.id)
        dialog.close()
        self.refresh()
        ui.notify(f"Deleted {prompt.name}")

    def start_wizard(self, prompt):
        # Load full prompt to get template manifest
        full_prompt = self.db.prompts.get_by_id(prompt.id)
        wizard = SetupWizard(
            self.db, self.orchestrator, full_prompt, on_complete=self.session_list.refresh
        )
        wizard.open()
