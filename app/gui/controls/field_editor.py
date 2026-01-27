from nicegui import ui
from typing import Any, Callable
import logging

logger = logging.getLogger(__name__)


class FieldEditorDialog:
    """
    A Prefab-aware popup dialog for editing a single field.
    """

    def __init__(
        self,
        label: str,
        path: str,
        prefab: str,
        current_value: Any,
        constraints: dict | None = None,  # e.g., {"min": 0, "max": 20}
        on_save: Callable[[str, Any], None] = None,
    ):
        self.label = label
        self.path = path
        self.prefab = prefab
        self.current_value = current_value
        self.constraints = constraints or {}
        self.on_save = on_save
        self.dialog = None
        self.input_ref = None

    def open(self):
        """Opens the editor dialog."""
        try:
            logger.debug(f"FieldEditorDialog.open() called for {self.path}, prefab={self.prefab}")
            with ui.dialog() as self.dialog, ui.card().classes("p-4 min-w-[300px] bg-slate-900 border border-slate-700"):
                ui.label(f"Edit: {self.label}").classes("text-lg font-bold mb-2 text-white")
                ui.label(f"Path: {self.path}").classes("text-xs text-gray-400 mb-4 font-mono")

                # Render input based on Prefab
                self._render_input()

                # Action Buttons
                with ui.row().classes("w-full justify-end gap-2 mt-4"):
                    ui.button("Cancel", on_click=self.dialog.close).props("flat")
                    ui.button("Save", on_click=self._handle_save).classes("bg-green-700 text-white")

            logger.debug("Dialog created, calling dialog.open()")
            self.dialog.open()
            logger.debug("Dialog.open() completed")
        except Exception as e:
            logger.error(f"FieldEditorDialog.open() failed: {e}", exc_info=True)
            ui.notify(f"Dialog error: {e}", type="negative")

    def _render_input(self):
        """Renders the appropriate input widget based on Prefab type."""

        if self.prefab == "VAL_INT":
            self.input_ref = ui.number(
                label="Value",
                value=self.current_value if self.current_value is not None else 0,
                min=self.constraints.get("min"),
                max=self.constraints.get("max"),
                precision=0,
            ).classes("w-full").props('dark standout')

        elif self.prefab == "VAL_BOOL":
            self.input_ref = ui.switch(
                text="Active",
                value=bool(self.current_value),
            ).classes("text-gray-300")

        elif self.prefab == "VAL_TEXT":
            self.input_ref = ui.textarea(
                label="Value",
                value=str(self.current_value or ""),
            ).classes("w-full").props('dark standout autogrow')

        elif self.prefab == "VAL_STEP_DIE":
            # Dropdown for die types
            options = ["d4", "d6", "d8", "d10", "d12", "d20"]
            self.input_ref = ui.select(
                options=options,
                value=self.current_value or "d6",
                label="Die Type",
            ).classes("w-full").props('dark standout')

        elif self.prefab == "VAL_COMPOUND":
            # Two fields: score and mod
            with ui.column().classes("w-full gap-2"):
                self.input_ref = {}
                score_val = (
                    self.current_value.get("score")
                    if isinstance(self.current_value, dict)
                    else 10
                )
                mod_val = (
                    self.current_value.get("mod")
                    if isinstance(self.current_value, dict)
                    else 0
                )
                
                self.input_ref["score"] = ui.number(
                    label="Score",
                    value=score_val,
                    precision=0,
                ).classes("w-full").props('dark standout')
                
                self.input_ref["mod"] = ui.number(
                    label="Modifier",
                    value=mod_val,
                    precision=0,
                ).classes("w-full").props('dark standout')

        elif self.prefab == "RES_POOL":
            # Two fields: current and max
            with ui.column().classes("w-full gap-2"):
                self.input_ref = {}
                val = self.current_value if isinstance(self.current_value, dict) else {"current": 0, "max": 0}
                self.input_ref["current"] = ui.number(
                    label="Current",
                    value=val.get("current", 0),
                    precision=0,
                ).classes("w-full").props('dark standout')
                self.input_ref["max"] = ui.number(
                    label="Maximum",
                    value=val.get("max", 0),
                    precision=0,
                ).classes("w-full").props('dark standout')

        elif self.prefab == "RES_TRACK":
            # Render as a row of toggleable boxes
            track = self.current_value if isinstance(self.current_value, list) else []
            with ui.row().classes("gap-2 items-center"):
                ui.label("Marked:").classes("text-xs text-gray-400")
                self.input_ref = []
                for state in track:
                    cb = ui.checkbox(value=state)
                    self.input_ref.append(cb)

        elif self.prefab == "RES_COUNTER":
            self.input_ref = ui.number(
                label="Count",
                value=self.current_value or 0,
                precision=0,
            ).classes("w-full").props('dark standout')

        elif self.prefab == "VAL_JSON":
            import json
            default_val = "{}"
            try:
                if isinstance(self.current_value, (dict, list)):
                    default_val = json.dumps(self.current_value, indent=2)
                else:
                    default_val = str(self.current_value)
            except Exception as e:
                logger.warning(f"Failed to serialize value: {e}", exc_info=True)
                pass
                
            self.input_ref = ui.textarea(
                label="JSON Data",
                value=default_val,
            ).classes("w-full font-mono text-xs").props('dark standout autogrow input-class="font-mono"')

        else:
            # Fallback: Generic text input
            ui.label(f"Unsupported Prefab: {self.prefab}. Using text fallback.").classes("text-yellow-500 text-xs mb-2")
            self.input_ref = ui.input(
                label="Value",
                value=str(self.current_value),
            ).classes("w-full").props('dark standout')

    def _handle_save(self):
        """Extracts the new value and calls the on_save callback."""
        new_value = self._extract_value()
        if self.on_save:
            self.on_save(self.path, new_value)
        self.dialog.close()

    def _extract_value(self) -> Any:
        """Extracts the value from the input widget(s)."""

        if self.prefab in ["VAL_INT", "VAL_BOOL", "VAL_TEXT", "VAL_STEP_DIE", "RES_COUNTER"]:
            return self.input_ref.value

        elif self.prefab == "VAL_COMPOUND":
            return {
                "score": int(self.input_ref["score"].value or 0),
                "mod": int(self.input_ref["mod"].value or 0),
            }

        elif self.prefab == "RES_POOL":
            return {
                "current": int(self.input_ref["current"].value or 0),
                "max": int(self.input_ref["max"].value or 0),
            }

        elif self.prefab == "RES_TRACK":
            return [cb.value for cb in self.input_ref]

        elif self.prefab == "VAL_JSON":
            import json
            try:
                return json.loads(self.input_ref.value)
            except Exception as e:
                ui.notify(f"Invalid JSON: {e}", type="negative")
                # Return original string if parse fails? Or maybe raise error?
                # For now, let's return the string but the service might reject it if it expects a dict
                # Ideally we should stop the save here... but on_save is called after this.
                # Let's hope the user fixes it.
                return self.input_ref.value

        else:
            # Fallback
            return self.input_ref.value
