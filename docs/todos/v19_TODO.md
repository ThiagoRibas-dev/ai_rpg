# Universal Field Editor Specification

## Overview

This document specifies the implementation of a **Universal Field Editor** system that allows users to manually edit character stats, resources, and inventory directly from the UI, while still respecting the game's validation rules (Manifests, Prefab constraints, Formulas).

---

## Goals

1. **Direct Editing**: Users can click on any stat/resource to edit it inline or via a popup.
2. **Validation Enforcement**: All edits pass through the `ValidationPipeline` to enforce constraints (e.g., HP ≤ Max HP).
3. **Audit Trail**: Optionally log manual edits as "system" events for debugging/transparency.
4. **Prefab-Aware UI**: The editor adapts its input type based on the field's Prefab (e.g., slider for `RES_POOL`, toggle for `VAL_BOOL`).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         UI Layer                                │
│  ┌───────────────────┐    ┌───────────────────────────────────┐ │
│  │ CharacterInspector│───▶│ FieldEditorDialog                 │ │
│  │ InventoryInspector│    │ (Prefab-aware input component)    │ │
│  └───────────────────┘    └───────────────────────────────────┘ │
│            │                              │                     │
│            ▼                              ▼                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    ManualEditBridge                         ││
│  │  (Receives edit requests from UI, dispatches to service)   ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                  ManualEditService                          ││
│  │  - Parses path (e.g., "resources.hp.current")              ││
│  │  - Constructs Tool payload (Set or Adjust)                 ││
│  │  - Executes via ToolExecutor (bypasses LLM)                ││
│  │  - ValidationPipeline enforces constraints                 ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ game_state   │  │ ValidationPi-│  │ Manifest (Source of    │ │
│  │ (SQLite)     │  │ peline       │  │ Truth for Constraints) │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. `FieldEditorDialog` (UI Component)

**Location**: `app/gui/controls/field_editor.py`

A reusable dialog component that renders the appropriate input based on the field's Prefab.

```python
# app/gui/controls/field_editor.py

from nicegui import ui
from typing import Any, Callable

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
        with ui.dialog() as self.dialog, ui.card().classes("p-4 min-w-[300px]"):
            ui.label(f"Edit: {self.label}").classes("text-lg font-bold mb-2")
            ui.label(f"Path: {self.path}").classes("text-xs text-gray-500 mb-4")

            # Render input based on Prefab
            self._render_input()

            # Action Buttons
            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Cancel", on_click=self.dialog.close).props("flat")
                ui.button("Save", on_click=self._handle_save).classes("bg-green-600")

        self.dialog.open()

    def _render_input(self):
        """Renders the appropriate input widget based on Prefab type."""

        if self.prefab == "VAL_INT":
            self.input_ref = ui.number(
                label="Value",
                value=self.current_value or 0,
                min=self.constraints.get("min"),
                max=self.constraints.get("max"),
            ).classes("w-full")

        elif self.prefab == "VAL_BOOL":
            self.input_ref = ui.switch(
                text="Enabled",
                value=bool(self.current_value),
            )

        elif self.prefab == "VAL_TEXT":
            self.input_ref = ui.input(
                label="Value",
                value=str(self.current_value or ""),
            ).classes("w-full")

        elif self.prefab == "VAL_STEP_DIE":
            # Dropdown for die types
            options = ["d4", "d6", "d8", "d10", "d12"]
            self.input_ref = ui.select(
                options=options,
                value=self.current_value or "d6",
                label="Die Type",
            ).classes("w-full")

        elif self.prefab == "VAL_COMPOUND":
            # Two fields: score and mod
            with ui.column().classes("w-full gap-2"):
                self.input_ref = {}
                self.input_ref["score"] = ui.number(
                    label="Score",
                    value=self.current_value.get("score", 10) if isinstance(self.current_value, dict) else 10,
                ).classes("w-full")
                self.input_ref["mod"] = ui.number(
                    label="Modifier",
                    value=self.current_value.get("mod", 0) if isinstance(self.current_value, dict) else 0,
                ).classes("w-full")

        elif self.prefab == "RES_POOL":
            # Two fields: current and max
            with ui.column().classes("w-full gap-2"):
                self.input_ref = {}
                val = self.current_value if isinstance(self.current_value, dict) else {"current": 0, "max": 0}
                self.input_ref["current"] = ui.number(
                    label="Current",
                    value=val.get("current", 0),
                ).classes("w-full")
                self.input_ref["max"] = ui.number(
                    label="Maximum",
                    value=val.get("max", 0),
                ).classes("w-full")

        elif self.prefab == "RES_TRACK":
            # Render as a row of toggleable boxes
            track = self.current_value if isinstance(self.current_value, list) else []
            with ui.row().classes("gap-2"):
                self.input_ref = []
                for i, state in enumerate(track):
                    cb = ui.checkbox(value=state).classes("text-red-500")
                    self.input_ref.append(cb)

        elif self.prefab == "RES_COUNTER":
            self.input_ref = ui.number(
                label="Count",
                value=self.current_value or 0,
            ).classes("w-full")

        else:
            # Fallback: Generic text input
            ui.label("Unsupported Prefab. Using text input.").classes("text-yellow-500 text-xs")
            self.input_ref = ui.input(
                label="Value (JSON)",
                value=str(self.current_value),
            ).classes("w-full")

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
                "score": int(self.input_ref["score"].value),
                "mod": int(self.input_ref["mod"].value),
            }

        elif self.prefab == "RES_POOL":
            return {
                "current": int(self.input_ref["current"].value),
                "max": int(self.input_ref["max"].value),
            }

        elif self.prefab == "RES_TRACK":
            return [cb.value for cb in self.input_ref]

        else:
            # Fallback: try to parse as JSON or return string
            try:
                import json
                return json.loads(self.input_ref.value)
            except Exception:
                return self.input_ref.value
```

---

### 2. `ManualEditService` (Backend Service)

**Location**: `app/services/manual_edit_service.py`

This service handles the actual state mutation. It uses the existing `ToolExecutor` infrastructure to ensure all edits pass through validation.

```python
# app/services/manual_edit_service.py

import logging
from typing import Any
from app.tools.executor import ToolExecutor
from app.tools.schemas import Set
from app.setup.setup_manifest import SetupManifest
from app.database.db_manager import DBManager

logger = logging.getLogger(__name__)


class ManualEditService:
    """
    Service for manual (user-initiated) state edits.
    Bypasses the LLM but uses the ToolExecutor + ValidationPipeline.
    """

    def __init__(self, db_manager: DBManager, tool_registry, vector_store):
        self.db = db_manager
        self.tool_registry = tool_registry
        self.vector_store = vector_store

    def update_field(
        self,
        session_id: int,
        entity_type: str,
        entity_key: str,
        path: str,
        new_value: Any,
    ) -> dict:
        """
        Updates a single field on an entity.

        Args:
            session_id: The game session ID.
            entity_type: e.g., "character", "location".
            entity_key: e.g., "player", "npc_goblin".
            path: The dot-notation path to the field, e.g., "resources.hp.current".
            new_value: The new value to set.

        Returns:
            A dict with "success" and optional "message" or "error".
        """
        game_session = self.db.sessions.get_by_id(session_id)
        if not game_session:
            return {"success": False, "error": "Session not found."}

        # Build the full path including entity prefix
        full_path = f"{entity_type}.{entity_key}.{path}"

        # Construct the Set tool payload
        set_tool = Set(
            path=full_path,
            value=new_value,
        )

        # Get Manifest for validation context
        setup_data = SetupManifest(self.db).get_manifest(session_id)
        manifest_id = setup_data.get("manifest_id")
        manifest = self.db.manifests.get_by_id(manifest_id) if manifest_id else None

        # Execute via ToolExecutor (this triggers ValidationPipeline)
        executor = ToolExecutor(
            self.tool_registry,
            self.db,
            self.vector_store,
            ui_queue=None,  # No UI queue for manual edits
            logger=logger,
        )

        try:
            results, _ = executor.execute(
                tools=[set_tool],
                game_session=game_session,
                manifest_dict=setup_data,
                tool_budget=1,
                current_game_time=game_session.game_time,
                extra_context={"manifest": manifest, "source": "manual_edit"},
                turn_id="manual",
            )

            if results and results[0].get("result", {}).get("status") == "ok":
                logger.info(f"Manual edit: {full_path} = {new_value}")
                return {"success": True, "message": f"Updated {path}"}
            else:
                error = results[0].get("result", {}).get("error", "Unknown error")
                return {"success": False, "error": error}

        except Exception as e:
            logger.error(f"Manual edit failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
```

---

### 3. Integration with `CharacterInspector`

We modify the inspector to make fields clickable and trigger the editor dialog.

```python
# In app/gui/inspectors/character.py (modified _render_field method)

from app.gui.controls.field_editor import FieldEditorDialog

def _render_field(self, field_def, entity):
    val = get_path(entity, field_def.path)
    prefab = field_def.prefab
    label = field_def.label
    path = field_def.path

    # --- VAL_INT Example ---
    if prefab == "VAL_INT":
        with ui.row().classes("w-full justify-between items-center mb-1 cursor-pointer hover:bg-slate-700/50 rounded p-1"):
            ui.label(label).classes("text-sm text-gray-300")
            ui.label(str(val)).classes("font-mono font-bold text-blue-300")

            # Click handler to open editor
            def open_editor(p=path, l=label, pr=prefab, v=val):
                FieldEditorDialog(
                    label=l,
                    path=p,
                    prefab=pr,
                    current_value=v,
                    on_save=self._handle_field_save,
                ).open()

        # Attach click event to the row
        # (NiceGUI approach: wrap in a clickable element or use .on('click'))

    # ... similar for other prefabs

def _handle_field_save(self, path: str, new_value: Any):
    """Callback when a field is saved via the editor."""
    if not self.session_id:
        ui.notify("No session active", type="negative")
        return

    # Import the service (or get from orchestrator)
    from app.services.manual_edit_service import ManualEditService

    service = ManualEditService(
        self.db,
        self.orchestrator.tool_registry,
        self.orchestrator.vector_store,
    )

    result = service.update_field(
        session_id=self.session_id,
        entity_type="character",
        entity_key=self.entity_key,
        path=path,
        new_value=new_value,
    )

    if result.get("success"):
        ui.notify(f"✓ {result.get('message')}", type="positive")
        self.refresh()  # Reload the inspector
    else:
        ui.notify(f"✗ {result.get('error')}", type="negative")
```

---

### 4. Quick Edit Controls (Inline Buttons)

For common actions like +/- on resources, we can add inline buttons without opening a dialog.

```python
# Example: RES_POOL with +/- buttons

elif prefab == "RES_POOL":
    if not isinstance(val, dict):
        val = {"current": 0, "max": 0}
    curr = val.get("current", 0)
    mx = val.get("max", 0)

    with ui.column().classes("w-full mb-2"):
        with ui.row().classes("w-full justify-between items-center"):
            ui.label(label).classes("font-bold text-sm")

            # Quick +/- Buttons
            with ui.row().classes("gap-1"):
                ui.button("-", on_click=lambda p=path: self._quick_adjust(p, -1)).props(
                    "flat dense round size=xs"
                ).classes("text-red-400")

                ui.label(f"{curr} / {mx}").classes("text-sm min-w-[50px] text-center")

                ui.button("+", on_click=lambda p=path: self._quick_adjust(p, +1)).props(
                    "flat dense round size=xs"
                ).classes("text-green-400")

        # Progress bar
        pct = max(0, min(1, curr / mx)) if mx > 0 else 0
        ui.linear_progress(value=pct, size="8px", show_value=False).classes("rounded")

def _quick_adjust(self, path: str, delta: int):
    """Quick +/- adjustment for RES_POOL fields."""
    # Use the Adjust tool instead of Set
    from app.tools.schemas import Adjust
    # ... similar to _handle_field_save but with Adjust tool
```

---

## UI Flow Summary

```
┌────────────────────────────────────────────────────────────────────┐
│  User clicks on "Strength: 18" in the Stats panel                 │
└────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│  FieldEditorDialog opens with:                                     │
│  - Label: "Strength"                                               │
│  - Path: "attributes.strength"                                     │
│  - Prefab: "VAL_INT"                                               │
│  - Current Value: 18                                               │
│  - A number input widget                                           │
└────────────────────────────────────────────────────────────────────┘
                               │
                               ▼ (User changes to 16, clicks Save)
┌────────────────────────────────────────────────────────────────────┐
│  ManualEditService.update_field() is called                        │
│  - Constructs Set(path="character.player.attributes.strength",     │
│                   value=16)                                        │
│  - Executes via ToolExecutor                                       │
│  - ValidationPipeline runs (checks constraints, recalculates       │
│    derived values like modifiers)                                  │
└────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│  State is saved to DB                                              │
│  CharacterInspector.refresh() is called                            │
│  UI now shows "Strength: 16"                                       │
└────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Core Infrastructure
1. Create `FieldEditorDialog` component with support for basic prefabs (`VAL_INT`, `VAL_BOOL`, `VAL_TEXT`).
2. Create `ManualEditService` with `update_field()` method.
3. Integrate with `CharacterInspector` for attribute fields only.

### Phase 2: Resource Editing
1. Add support for `RES_POOL` (current/max editors).
2. Add quick +/- inline buttons for resources.
3. Add support for `RES_TRACK` (clickable pips).

### Phase 3: Inventory Editing
1. Add item quantity editing.
2. Add "Add Item" button with name/qty input.
3. Add "Remove Item" confirmation.

### Phase 4: Polish
1. Add undo/redo support (optional).
2. Add "GM Mode" toggle to disable validation for power users.
3. Add audit log entries for manual edits.

---

## Open Questions

1. **Formulas**: If a user edits a base stat that affects derived values (e.g., changing STR affects STR_MOD), should we:
   - (a) Auto-recalculate dependent fields? ✓ (Current plan via ValidationPipeline)
   - (b) Warn the user about cascading changes?

2. **Permissions**: Should there be a "Lock" mode where edits are disabled during gameplay?

3. **Inventory Structure**: For `CONT_LIST`, should the editor support:
   - (a) Only editing existing items?
   - (b) Adding/removing items?
   - (c) Reordering?

---

## Dependencies

- **Existing**: `ToolExecutor`, `ValidationPipeline`, `Set`/`Adjust` tools, `SetupManifest`, `Manifest`.
- **New**: `FieldEditorDialog`, `ManualEditService`.

---

## File Changes Summary

| File | Change |
|------|--------|
| `app/gui/controls/field_editor.py` | **NEW** - FieldEditorDialog component |
| `app/services/manual_edit_service.py` | **NEW** - Backend service for manual edits |
| `app/gui/inspectors/character.py` | **MODIFY** - Add click handlers, integrate editor |
| `app/gui/inspectors/inventory.py` | **MODIFY** - Add edit capabilities for items |
