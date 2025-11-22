import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any
from app.database.db_manager import DBManager
from app.tools.builtin._state_storage import get_all_of_type, get_entity

class SceneMapPanel(ttk.Frame):
    def __init__(self, parent, db_manager: DBManager, **kwargs):
        super().__init__(parent, **kwargs)
        self.db_manager = db_manager
        self.session_id: Optional[int] = None
        self.canvas = tk.Canvas(self, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.create_text(10, 10, anchor=tk.NW, text="Scene Map Panel", fill="white")

    def set_session(self, session_id: int):
        self.session_id = session_id

    def refresh(self):
        # This method will be called to update the scene map
        self.canvas.delete("all")
        if self.session_id is not None:
            self.canvas.create_text(10, 10, anchor=tk.NW, text=f"Scene Map for session {self.session_id}", fill="white")
            with self.db_manager as db:
                active_scene = get_entity(self.session_id, db, "scene", "active_scene")
                characters = get_all_of_type(self.session_id, db, "character")
                
                if active_scene:
                    self._draw_scene_map(active_scene, characters)
                else:
                    self.canvas.create_text(10, 10, anchor=tk.NW, text="No active scene.", fill="white")
        else:
            self.canvas.create_text(10, 10, anchor=tk.NW, text="No session loaded", fill="white")

    def _draw_scene_map(self, active_scene: Dict[str, Any], characters: Dict[str, Any]):
        zones = active_scene.get("zones", [])
        if not zones:
            self.canvas.create_text(10, 10, anchor=tk.NW, text="No zones defined for this scene.", fill="white")
            return

        zone_positions = self._calculate_zone_layout(zones)
        
        zone_width, zone_height = 120, 60
        
        # Draw Zones
        for zone_data in zones:
            zone_id = zone_data["id"]
            pos = zone_positions.get(zone_id)
            if not pos:
                continue
            
            x, y = pos
            x1, y1 = x - zone_width / 2, y - zone_height / 2
            x2, y2 = x + zone_width / 2, y + zone_height / 2
            
            self.canvas.create_rectangle(x1, y1, x2, y2, outline="white", fill="gray20", width=2)
            self.canvas.create_text(x, y - 15, text=zone_data.get("name", zone_id), fill="white", width=zone_width - 10)

        # Draw Characters
        for char_key, char_data in characters.items():
            scene_state = char_data.get("scene_state", {})
            zone_id = scene_state.get("zone_id")
            is_hidden = scene_state.get("is_hidden", False)

            if zone_id and not is_hidden:
                pos = zone_positions.get(zone_id)
                if pos:
                    char_symbol = "@" if char_key == "player" else char_data.get("name", "NPC")[0].upper()
                    self.canvas.create_text(pos[0], pos[1] + 15, text=char_symbol, fill="red", font=("Arial", 16, "bold"))


    def _calculate_zone_layout(self, zones: list[Dict[str, Any]]) -> Dict[str, tuple[int, int]]:
        """
        Calculates layout for zones. Prioritizes x,y in zone data, then a simple grid.
        """
        positions = {}
        # Track occupied grid cells to assign new ones
        occupied_cells = set() 
        
        # First pass: use explicit x,y coordinates if available
        for zone in zones:
            if "x" in zone and "y" in zone:
                grid_x, grid_y = zone["x"], zone["y"]
                # Convert grid coords to canvas coords
                canvas_x = 100 + grid_x * 150
                canvas_y = 50 + grid_y * 100
                positions[zone["id"]] = (canvas_x, canvas_y)
                occupied_cells.add((grid_x, grid_y))
        
        # Second pass: assign positions for zones without explicit x,y
        current_grid_x, current_grid_y = 0, 0
        for zone in zones:
            if zone["id"] not in positions: # If not already positioned
                while (current_grid_x, current_grid_y) in occupied_cells:
                    current_grid_x += 1
                    if current_grid_x >= 4: # Max 4 columns before new row
                        current_grid_x = 0
                        current_grid_y += 1
                
                canvas_x = 100 + current_grid_x * 150
                canvas_y = 50 + current_grid_y * 100
                positions[zone["id"]] = (canvas_x, canvas_y)
                occupied_cells.add((current_grid_x, current_grid_y))
        
        return positions
