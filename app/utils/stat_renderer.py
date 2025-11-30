from typing import Any, Dict, Optional


def render_stat_string(
    value: Any, widget_type: str, rendering_meta: Optional[Dict[str, Any]] = None
) -> str:
    """
    Converts a raw value into a formatted display string based on widget type.
    Used by both the GUI (Inspector) and the LLM Context Builder.

    Args:
        value: The raw data (int, str, etc.)
        widget_type: The UI hint (e.g., 'ladder', 'bonus', 'die')
        rendering_meta: The 'rendering' dictionary from the schema (contains lookup_maps, etc.)
    """
    if rendering_meta is None:
        rendering_meta = {}

    str_val = str(value)

    # 1. Fate/Ladder Style (e.g., 3 -> "Good (+3)")
    if widget_type == "ladder":
        lookup = rendering_meta.get("lookup_map", {})
        # JSON keys are always strings, so convert value to str for lookup
        adjective = lookup.get(str_val)

        if adjective:
            # Format: "Adjective (+N)"
            try:
                val_int = int(value)
                sign = "+" if val_int >= 0 else ""
                return f"{adjective} ({sign}{val_int})"
            except (ValueError, TypeError):
                return f"{adjective} ({value})"
        return str_val

    # 2. Bonus Style (e.g., 3 -> "+3")
    elif widget_type == "bonus":
        try:
            val_float = float(value)
            if val_float >= 0:
                return f"+{value}"
        except (ValueError, TypeError):
            pass
        return str_val

    # 3. Dice Style (e.g., "d6" - mostly passthrough, but ready for future formatting)
    elif widget_type == "die":
        return str_val

    # 4. Gauge/Pool Style (Pass-through, usually handled by caller, but safety check)
    # Context Builder handles Gauges separately usually (Current/Max)

    # Default
    return str_val


def render_stat_from_model(value: Any, stat_def: Any) -> str:
    """
    Helper to extract widget/meta from a Pydantic model (StatValue, StatTrack)
    and render the string.
    """
    if not stat_def:
        return str(value)

    widget = getattr(stat_def, "widget", "text")

    # Extract rendering meta if it exists and convert to dict
    meta = {}
    if hasattr(stat_def, "rendering") and stat_def.rendering:
        # Check if it's a Pydantic model or dict
        if hasattr(stat_def.rendering, "model_dump"):
            meta = stat_def.rendering.model_dump()
        elif isinstance(stat_def.rendering, dict):
            meta = stat_def.rendering

    return render_stat_string(value, widget, meta)
