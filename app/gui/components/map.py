from nicegui import ui
import math


class MapComponent:
    def __init__(self, bridge, db_manager):
        self.bridge = bridge
        self.db = db_manager
        self.container = None
        self.content = None
        self.mode = "tactical"  # 'tactical' or 'world'
        self.session_id = None

        self.tactical_data = {"width": 5, "height": 5, "entities": {}, "terrain": {}}
        self.world_data = {"center": None, "neighbors": {}}

        if hasattr(self.bridge, "register_map"):
            self.bridge.register_map(self)

    def set_session(self, session_id: int):
        self.session_id = session_id
        self.refresh_from_db()

    def refresh_from_db(self):
        if not self.session_id:
            return

        try:
            from app.services.state_service import get_entity

            scene = get_entity(self.session_id, self.db, "scene", "active_scene")

            if scene and "tactical_map" in scene:
                tmap = scene["tactical_map"]
                entities = {}
                if "positions" in tmap:
                    for k, v in tmap["positions"].items():
                        entities[v] = k

                self.tactical_data = {
                    "width": tmap.get("width", 5),
                    "height": tmap.get("height", 5),
                    "terrain": tmap.get("terrain", {}),
                    "entities": entities,
                }

            if scene and "location_key" in scene:
                loc_key = scene["location_key"]
                loc = get_entity(self.session_id, self.db, "location", loc_key)
                if loc:
                    self.world_data = {
                        "center": loc_key,
                        "neighbors": loc.get("connections", {}),
                    }

            self.redraw()
        except Exception as e:
            print(f"Map refresh error: {e}")

    def render(self):
        with ui.column().classes("w-full p-0 gap-0"):
            with ui.row().classes(
                "w-full bg-slate-900 p-2 items-center justify-between border-b border-slate-700"
            ):
                with ui.row().classes("gap-1"):
                    ui.icon("map").classes("text-gray-400")
                    ui.label("Visuals").classes("font-bold text-gray-200")

                with ui.button_group().props("flat"):
                    ui.button(
                        "Tactical", on_click=lambda: self.set_mode("tactical")
                    ).props("dense")
                    ui.button("World", on_click=lambda: self.set_mode("world")).props(
                        "dense"
                    )

            # ✅ FIX: Added sanitize=False
            self.content = ui.html("", sanitize=False).classes(
                "w-full bg-slate-950 flex justify-center items-center overflow-hidden"
            )

    def set_mode(self, mode):
        self.mode = mode
        self.redraw()

    def update_tactical(self, data):
        self.tactical_data = data
        if self.mode == "tactical":
            self.redraw()

    def redraw(self):
        if not self.content:
            return

        if self.mode == "tactical":
            svg = self._generate_tactical_svg()
        else:
            svg = self._generate_world_svg()

        self.content.set_content(svg)

    def _generate_tactical_svg(self):
        w, h = self.tactical_data.get("width", 5), self.tactical_data.get("height", 5)
        entities = self.tactical_data.get("entities", {})
        cell_size = 50
        svg_w, svg_h = w * cell_size, h * cell_size

        svg_parts = [
            f'<svg width="100%" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg">'
        ]

        for y in range(h):
            for x in range(w):
                cx, cy = x * cell_size, (h - 1 - y) * cell_size
                coord = f"{chr(65 + x)}{y + 1}"

                fill = "#1e293b"
                stroke = "#334155"

                svg_parts.append(
                    f'<rect x="{cx}" y="{cy}" width="{cell_size}" height="{cell_size}" fill="{fill}" stroke="{stroke}" />'
                )
                svg_parts.append(
                    f'<text x="{cx + 2}" y="{cy + 10}" font-size="8" fill="#64748b" font-family="monospace">{coord}</text>'
                )

                if coord in entities:
                    key = entities[coord]
                    initial = key.split(":")[-1][0].upper()
                    is_player = "player" in key

                    circle_fill = "#d97706" if is_player else "#dc2626"
                    svg_parts.append(
                        f'<circle cx="{cx + 25}" cy="{cy + 25}" r="15" fill="{circle_fill}" />'
                    )
                    svg_parts.append(
                        f'<text x="{cx + 25}" y="{cy + 30}" font-size="14" fill="white" text-anchor="middle" font-weight="bold">{initial}</text>'
                    )

        svg_parts.append("</svg>")
        return "".join(svg_parts)

    def _generate_world_svg(self):
        center_key = self.world_data.get("center", "Unknown")
        neighbors = self.world_data.get("neighbors", {})

        cx, cy = 200, 150
        radius = 100
        svg_parts = [
            '<svg width="100%" height="300" viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg">'
        ]

        count = len(neighbors)
        if count > 0:
            angle_step = 360 / count
            for i, (direction, data) in enumerate(neighbors.items()):
                angle_rad = math.radians(i * angle_step - 90)
                nx = cx + radius * math.cos(angle_rad)
                ny = cy + radius * math.sin(angle_rad)

                svg_parts.append(
                    f'<line x1="{cx}" y1="{cy}" x2="{nx}" y2="{ny}" stroke="#475569" stroke-width="2" />'
                )

                name = data.get("display_name", "???")
                svg_parts.append(
                    f'<circle cx="{nx}" cy="{ny}" r="25" fill="#334155" stroke="#94a3b8" stroke-width="2" />'
                )
                svg_parts.append(
                    f'<text x="{nx}" y="{ny + 40}" font-size="10" fill="#cbd5e1" text-anchor="middle">{name[:10]}</text>'
                )
                svg_parts.append(
                    f'<text x="{(cx + nx) / 2}" y="{(cy + ny) / 2}" font-size="9" fill="#64748b" text-anchor="middle" background="black">{direction}</text>'
                )

        svg_parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="35" fill="#d97706" stroke="#fbbf24" stroke-width="3" />'
        )
        svg_parts.append(
            f'<text x="{cx}" y="{cy + 5}" font-size="12" fill="white" text-anchor="middle" font-weight="bold">{center_key[:8]}</text>'
        )

        svg_parts.append("</svg>")
        return "".join(svg_parts)
