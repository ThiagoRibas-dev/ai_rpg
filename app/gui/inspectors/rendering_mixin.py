import re
from typing import TYPE_CHECKING, Any

from nicegui import ui

from app.models.vocabulary import ConfigKey, FieldKey, ManifestValueType, PrefabID
from app.prefabs.validation import get_path
from app.services.state_service import get_entity

if TYPE_CHECKING:
    from app.core.orchestrator import Orchestrator
    from app.database.db_manager import DBManager


class RenderingMixin:
    """
    Shared rendering logic for inspectors (Lego Protocol).
    """
    db: "DBManager"
    orchestrator: "Orchestrator"
    session_id: int | None
    entity_key: str

    def _detect_pool_keys(self, item: Any) -> tuple[str | None, str | None]:
        """Identifies current/max key pairs in a dict."""
        if not isinstance(item, dict):
            return None, None

        # 1. Standard keys
        if FieldKey.CURRENT in item and FieldKey.MAX in item:
            return FieldKey.CURRENT, FieldKey.MAX
        if "current" in item and "max" in item:
            return "current", "max"

        # 2. Suffix match (*_current, *_max)
        curr_keys = [k for k in item.keys() if k.endswith("_current")]
        for ck in curr_keys:
            base = ck[:-8] # strip _current
            mk = f"{base}_max"
            if mk in item:
                return ck, mk

        # 3. Fallback: First two numeric values
        numeric_keys = [k for k, v in item.items() if isinstance(v, int | float)]
        if len(numeric_keys) >= 2:
            return numeric_keys[0], numeric_keys[1]

        return None, None

    def _detect_item_prefab(self, item: Any, config: dict | None = None) -> tuple[str | None, dict[str, str]]:
        """
        3-layer detection algorithm for identifying list item structure:
        1. Schema: item_shape from config
        2. Shape: Match item keys to registered Prefab shapes
        3. Heuristic: Suffix matching & agnostic fallback
        """
        if not isinstance(item, dict):
            # --- Non-dict type detection ---
            if isinstance(item, list) and item and all(isinstance(x, bool) for x in item):
                return PrefabID.RES_TRACK, {}
            if isinstance(item, bool):
                return PrefabID.VAL_BOOL, {}
            if isinstance(item, int | float):
                return PrefabID.RES_COUNTER, {}
            if isinstance(item, str) and re.match(r'^\d*d\d+', item):
                return PrefabID.VAL_STEP_DIE, {}
            return None, {}

        # --- Layer 1: Schema-driven (item_shape from manifest) ---
        item_shape = (config or {}).get(ConfigKey.ITEM_SHAPE)
        if item_shape:
            # Check for standard RES_POOL suffixes
            curr_key = next((k for k in item_shape.keys() if k.endswith("_current")), None)
            max_key = next((k for k in item_shape.keys() if k.endswith("_max")), None)
            if curr_key and max_key:
                return PrefabID.RES_POOL, {"curr_key": curr_key, "max_key": max_key}

            # Check for VAL_COMPOUND
            if FieldKey.SCORE in item_shape and FieldKey.MOD in item_shape:
                return PrefabID.VAL_COMPOUND, {}

            # Check for VAL_LADDER
            if FieldKey.VALUE in item_shape and FieldKey.LABEL in item_shape:
                return PrefabID.VAL_LADDER, {}

        # --- Layer 2: Prefab shape matching (canonical shapes) ---
        item_keys = set(item.keys())

        # Exact match logic for common prefabs
        if {FieldKey.SCORE, FieldKey.MOD}.issubset(item_keys):
            return PrefabID.VAL_COMPOUND, {}

        if {FieldKey.VALUE, FieldKey.LABEL}.issubset(item_keys):
            return PrefabID.VAL_LADDER, {}

        if {FieldKey.CURRENT, FieldKey.MAX}.issubset(item_keys) or {"current", "max"}.issubset(item_keys):
            curr = FieldKey.CURRENT if FieldKey.CURRENT in item_keys else "current"
            mx = FieldKey.MAX if FieldKey.MAX in item_keys else "max"
            return PrefabID.RES_POOL, {"curr_key": curr, "max_key": mx}

        # --- Layer 3: Heuristic fallback ---
        pool_keys = self._detect_pool_keys(item)
        if pool_keys[0] and pool_keys[1]:
            return PrefabID.RES_POOL, {"curr_key": pool_keys[0], "max_key": pool_keys[1]}

        return None, {}

    def _get_item_label(self, item: Any, config: dict | None = None) -> str:
        """Helper to get just the label part of an agnostic item."""
        if not isinstance(item, dict):
            return str(item)
        item_shape: dict[str, str] = config.get(ConfigKey.ITEM_SHAPE, {}) if config else {}
        for key, type_name in item_shape.items():
            if type_name == ManifestValueType.STR and key in item:
                return str(item[key])
        for key in [FieldKey.NAME, FieldKey.LABEL]:
            if item.get(key):
                return str(item[key])
        return "Item"

    def _format_item_agnostic(self, item: Any, config: dict | None = None) -> str:
        """
        Recursively formats an item based on its shape and manifest metadata.
        Aligns with "Lego Protocol" (Prefabs).
        """
        if not isinstance(item, dict):
            # Handle primitive booleans
            if isinstance(item, bool):
                return "✓" if item else "✗"
            # Handle possible dice notation strings
            s = str(item)
            if any(d in s.lower() for d in ["d4", "d6", "d8", "d10", "d12", "d20"]):
                return f"[{s}]"
            return s

        item_shape = config.get(ConfigKey.ITEM_SHAPE, {}) if config else {}

        # 1. Identify Label(s)
        labels = []
        used_keys = set()

        # Try manifest hint first
        label_key = None
        for key, type_name in item_shape.items():
            if type_name == ManifestValueType.STR and key in item:
                label_key = key
                break

        # Fallback to standard name/label keys
        if not label_key:
            for k in [FieldKey.NAME, FieldKey.LABEL]:
                if item.get(k):
                    label_key = k
                    break

        if label_key:
            labels.append(str(item[label_key]))
            used_keys.add(label_key)

        # 2. Identify Values
        vals = []

        # Specific prefab detection for text summary
        keys = self._detect_pool_keys(item)
        if keys[0] and keys[1]:
            vals.append(f"{item[keys[0]]}/{item[keys[1]]}")
            used_keys.update(keys)
        elif FieldKey.SCORE in item and FieldKey.MOD in item:
            sign = "+" if item[FieldKey.MOD] >= 0 else ""
            vals.append(f"{item[FieldKey.SCORE]} ({sign}{item[FieldKey.MOD]})")
            used_keys.update([FieldKey.SCORE, FieldKey.MOD])

        # Collect remaining numeric/bool fields
        for k, v in item.items():
            if k in used_keys:
                continue
            if isinstance(v, int | float | bool):
                if not self.db:
                    continue
                fmt_v = self._format_item_agnostic(v)
                vals.append(f"{k}:{fmt_v}")

        label_part = " ".join(labels)
        val_part = ", ".join(vals)

        if label_part and val_part:
            return f"{label_part} ({val_part})"
        return label_part or val_part or "???"

    def _render_pool_widget(self, label: str, path: str, val: Any, config: dict | None = None, mini: bool = False, keys: tuple[str | None, str | None] | None = None):
        if not isinstance(val, dict):
            val = {}

        curr_key, max_key = keys if keys else self._detect_pool_keys(val)
        if not curr_key or not max_key:
            # Fallback to simple label if detection fails
            ui.label(label).classes("text-sm text-slate-300")
            ui.label(str(val)).classes("text-xs font-mono text-slate-500")
            return

        curr = val.get(curr_key, 0)
        mx = val.get(max_key, 0)
        pct = max(0, min(1, curr / mx)) if mx > 0 else 0

        with ui.column().classes("w-full mb-2" if not mini else "w-full"):
            with ui.row().classes("w-full justify-between items-center text-xs mb-1"):
                with ui.row().classes("items-center gap-1 cursor-pointer group").on("click", lambda: self._open_editor(label, path, PrefabID.RES_POOL, val)):
                    ui.label(label).classes("font-bold text-slate-300")
                    ui.icon("edit", size="10px").classes("text-slate-600 opacity-0 group-hover:opacity-100")

                # Quick +/- Buttons
                with ui.row().classes("items-center gap-1 bg-slate-800/50 rounded px-1"):
                    ui.button("-", on_click=lambda: self._quick_adjust(path, -1, config)).props("flat dense round size=xs color=red")
                    ui.label(f"{curr} / {mx}").classes("min-w-[40px] text-center font-mono")
                    ui.button("+", on_click=lambda: self._quick_adjust(path, 1, config)).props("flat dense round size=xs color=green")

            ui.linear_progress(value=pct, size="4px" if mini else "6px", show_value=False).classes("rounded bg-slate-700")

    def _render_counter_widget(self, label: str, path: str, val: Any, config: dict | None = None, mini: bool = False):
        with ui.row().classes("w-full justify-between items-center mb-1 rounded p-1 transition-colors cursor-pointer hover:bg-slate-700/40 group").on("click", lambda: self._open_editor(label, path, PrefabID.RES_COUNTER, val)):
            ui.label(label).classes("text-sm text-slate-300")
            with ui.row().classes("items-center gap-2"):
                ui.button("-", on_click=lambda e: (e.stop_propagation(), self._quick_adjust(path, -1, config))).props("flat dense round size=xs")
                ui.label(str(val)).classes("font-mono font-bold text-green-400 min-w-[20px] text-center")
                ui.button("+", on_click=lambda e: (e.stop_propagation(), self._quick_adjust(path, 1, config))).props("flat dense round size=xs")
                ui.icon("edit", size="12px").classes("text-slate-600 opacity-0 group-hover:opacity-100")

    def _render_track_widget(self, label: str, path: str, val: Any, config: dict | None = None, mini: bool = False):
        if not isinstance(val, list):
            val = []
        with ui.row().classes("w-full justify-between items-center mb-1 rounded p-1 transition-colors cursor-pointer hover:bg-slate-700/40 group").on("click", lambda: self._open_editor(label, path, PrefabID.RES_TRACK, val)):
            ui.label(label).classes("text-sm text-slate-300")
            with ui.row().classes("gap-1"):
                for state in val:
                    color = "text-red-500" if state else "text-slate-700"
                    ui.icon("circle").classes(f"text-[10px] {color}")
                ui.icon("edit", size="12px").classes("text-slate-600 opacity-0 group-hover:opacity-100")

    def _render_simple_val_widget(self, label: str, path: str, val: Any, prefab: str, config: dict | None = None, mini: bool = False):
        with ui.row().classes("w-full justify-between items-center mb-1 rounded p-1 transition-colors cursor-pointer hover:bg-slate-700/40 group").on("click", lambda: self._open_editor(label, path, prefab, val)):
            ui.label(label).classes("text-sm text-slate-300")

            with ui.row().classes("items-center gap-2"):
                if prefab == PrefabID.VAL_TEXT:
                    ui.label(str(val)).classes("text-sm text-white font-serif italic")
                elif prefab == PrefabID.VAL_INT:
                    ui.label(str(val)).classes("font-mono font-bold text-blue-300")
                elif prefab == PrefabID.VAL_COMPOUND:
                    if isinstance(val, dict):
                        score = val.get(FieldKey.SCORE, 0)
                        mod = val.get(FieldKey.MOD, 0)
                        sign = "+" if mod >= 0 else ""
                        ui.label(f"{score} ({sign}{mod})").classes("font-mono text-amber-300")
                    else:
                        ui.label(str(val))
                elif prefab == PrefabID.VAL_STEP_DIE:
                    ui.badge(str(val), color="purple").props("text-color=white")
                elif prefab == PrefabID.VAL_BOOL:
                    icon = "check_box" if val else "check_box_outline_blank"
                    color = "text-green-400" if val else "text-gray-600"
                    ui.icon(icon).classes(color)
                elif prefab == PrefabID.VAL_LADDER:
                    if isinstance(val, dict):
                        v = val.get(FieldKey.VALUE, 0)
                        lbl = val.get(FieldKey.LABEL, "")
                        sign = "+" if v >= 0 else ""
                        ui.label(f"{sign}{v} {lbl}").classes("text-sm text-cyan-300")
                    else:
                        ui.label(str(val))

                ui.icon("edit", size="12px").classes("text-slate-600 opacity-0 group-hover:opacity-100")

    def _quick_adjust(self, path: str, delta: int, config: dict | None = None):
        """Quickly adjust a resource current value."""
        if not self.session_id:
            return

        # Fetch current entity stats
        entity_key = getattr(self, "entity_key", "player")
        if not self.db:
             return
        entity = get_entity(self.session_id, self.db, "character", entity_key)
        if not entity:
            return

        full_val = get_path(entity, path)
        if isinstance(full_val, dict):
            # It's a pool, adjust the current value
            prefab_id, key_map = self._detect_item_prefab(full_val, config)
            if prefab_id == PrefabID.RES_POOL and "curr_key" in key_map:
                curr_key = key_map["curr_key"]
                new_val = full_val.get(curr_key, 0) + delta
                self._handle_field_save(f"{path}.{curr_key}", new_val)
                return

            # Fallback to old heuristic if detection fails
            alt_curr, _ = self._detect_pool_keys(full_val)
            if alt_curr:
                new_val = full_val.get(alt_curr, 0) + delta
                self._handle_field_save(f"{path}.{alt_curr}", new_val)
                return

        # It's a simple int or counter
        new_val = int(full_val or 0) + delta
        self._handle_field_save(path, new_val)

    def _prompt_add_item(self, path):
        """Show dialog to add a new item/tag."""
        new_val = {"name": "New Item", "description": ""}
        self._open_editor("Add New Item", path, "VAL_JSON", new_val, on_save=self._handle_list_add)

    def _handle_list_add(self, path, new_item):
        """Add an item to a list field."""
        if not self.session_id:
            return
        entity_key = getattr(self, "entity_key", "player")
        entity = get_entity(self.session_id, self.db, "character", entity_key)
        items = get_path(entity, path) or []
        if isinstance(items, list):
            items.append(new_item)
            self._handle_field_save(path, items)

    def _handle_list_update(self, path, index, new_item):
        """Update an item at a specific index in a list field."""
        if not self.session_id:
            return
        entity_key = getattr(self, "entity_key", "player")
        entity = get_entity(self.session_id, self.db, "character", entity_key)
        items = get_path(entity, path)
        if isinstance(items, list) and 0 <= index < len(items):
            items[index] = new_item
            self._handle_field_save(path, items)

    def _delete_list_item(self, path, index):
        """Remove an item from a list field."""
        if not self.session_id:
            return
        entity_key = getattr(self, "entity_key", "player")
        entity = get_entity(self.session_id, self.db, "character", entity_key)
        items = get_path(entity, path)
        if isinstance(items, list) and 0 <= index < len(items):
            items.pop(index)
            self._handle_field_save(path, items)

    # Sub-classes must implement
    def _open_editor(self, label, path, prefab, val, on_save=None):
        from app.gui.controls.field_editor import FieldEditorDialog
        FieldEditorDialog(
            label=label,
            path=path,
            prefab=prefab,
            current_value=val,
            on_save=on_save or self._handle_field_save,
        ).open()

    def _handle_field_save(self, path, value):
        raise NotImplementedError("Inheriting class must implement _handle_field_save")
