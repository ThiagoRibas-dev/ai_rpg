from nicegui import ui
from app.models.prompt import Prompt


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

        # No more Template JSON editing here - it happens at Session Start now.

    def open(self):
        with (
            self.dialog,
            ui.card().classes(
                "w-[800px] h-[700px] bg-slate-900 border border-slate-700 p-0"
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

            # Body
            with ui.column().classes("w-full h-full p-4 gap-4 scroll-y"):
                ui.input(label="System Name").bind_value(self, "name").classes("w-full")

                ui.label("System Instruction (The Persona)").classes(
                    "text-xs font-bold text-gray-500 uppercase mt-2"
                )
                ui.textarea(placeholder="You are the GM...").bind_value(
                    self, "content"
                ).classes("w-full").props("rows=4 outlined")

                ui.label("Rules Document (The Knowledge Base)").classes(
                    "text-xs font-bold text-gray-500 uppercase mt-2"
                )
                ui.label(
                    "Paste raw text rules here. The AI will read this to architect character sheets dynamically."
                ).classes("text-xs text-gray-600 italic")
                ui.textarea(placeholder="Paste rules text here...").bind_value(
                    self, "rules"
                ).classes("w-full flex-grow").props("rows=10 outlined")

            # Footer
            with ui.row().classes(
                "w-full bg-slate-950 p-4 justify-end gap-2 border-t border-slate-700 absolute bottom-0"
            ):
                ui.button("Cancel", on_click=self.dialog.close).props("flat")
                ui.button("Save System", on_click=self.save).classes("bg-green-600")

        self.dialog.open()

    def save(self):
        if not self.name or not self.content:
            ui.notify("Name and System Instruction are required.", type="negative")
            return

        if self.prompt:
            # Update
            self.prompt.name = self.name
            self.prompt.content = self.content
            self.prompt.rules_document = self.rules
            # We preserve existing template_manifest if it exists, just in case, but don't edit it.
            self.db.prompts.update(self.prompt)
            ui.notify(f"Updated '{self.name}'")
        else:
            # Create
            self.db.prompts.create(self.name, self.content, self.rules, "{}")
            ui.notify(f"Created '{self.name}'")

        if self.on_save:
            self.on_save()
        self.dialog.close()
