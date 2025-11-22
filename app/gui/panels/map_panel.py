import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any, Set
from app.database.db_manager import DBManager
from app.tools.builtin._state_storage import get_all_of_type, get_entity

class MapPanel(ttk.Frame):
    def __init__(self, parent, db_manager: DBManager, **kwargs):
        super().__init__(parent, **kwargs)
        self.db_manager = db_manager
        self.session_id: Optional[int] = None
        self.canvas = tk.Canvas(self, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.create_text(10, 10, anchor=tk.NW, text="Map Panel", fill="white")

    def set_session(self, session_id: int):
        self.session_id = session_id

    def refresh(self):
        # This method will be called to update the map
        self.canvas.delete("all")
        if self.session_id is not None:
            with self.db_manager as db:
                locations = get_all_of_type(self.session_id, db, "location")
                if locations:
                    # --- FOG OF WAR LOGIC ---
                    visited_keys: Set[str] = set()
                    
                    # 1. Get current location
                    active_scene = get_entity(self.session_id, db, "scene", "active_scene")
                    current_loc_key = active_scene.get("location_key")
                    if current_loc_key:
                        visited_keys.add(current_loc_key)
                        
                    # 2. Get locations from memories
                    memories = db.memories.get_by_session(self.session_id)
                    for mem in memories:
                        for tag in mem.tags_list():
                            if tag.startswith("location:"):
                                visited_keys.add(tag.split(":")[1])
                    
                    self._draw_map(locations, visited_keys, current_loc_key)
                else:
                    self.canvas.create_text(10, 10, anchor=tk.NW, text="No locations yet.", fill="white")
        else:
            self.canvas.create_text(10, 10, anchor=tk.NW, text="No session loaded", fill="white")

    def _draw_map(self, locations: Dict[str, Any], visited_keys: Set[str], current_loc_key: Optional[str]):
        # Filter locations to only include visited ones
        visited_locations = {key: val for key, val in locations.items() if key in visited_keys}
        if not visited_locations:
            self.canvas.create_text(10, 10, anchor=tk.NW, text="No visited locations to show.", fill="white")
            return

        node_positions = self._calculate_layout(visited_locations)
        
        # 1. Draw Edges
        for loc_key, loc_data in visited_locations.items():
            start_pos = node_positions.get(loc_key)
            if not start_pos:
                continue
            
            for connection_key in loc_data.get("connections", {}):
                # Only draw connection if the other end is also visited
                if connection_key in visited_keys:
                    end_pos = node_positions.get(connection_key)
                    if end_pos:
                        self.canvas.create_line(start_pos[0], start_pos[1], end_pos[0], end_pos[1], fill="gray50", width=1)

        # 2. Draw Nodes
        node_width, node_height = 100, 40
        for loc_key, pos in node_positions.items():
            x, y = pos
            x1, y1 = x - node_width / 2, y - node_height / 2
            x2, y2 = x + node_width / 2, y + node_height / 2
            
            # Highlight current location
            is_current = (loc_key == current_loc_key)
            outline_color = "yellow" if is_current else "cyan"
            
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=outline_color, fill="black", width=2)
            
            loc_name = locations[loc_key].get("name", "Unknown")
            self.canvas.create_text(x, y, text=loc_name, fill="white", width=node_width - 10)

    def _calculate_layout(self, locations: Dict[str, Any]) -> Dict[str, tuple[int, int]]:
        """Extremely simple grid layout for now."""
        positions = {}
        x, y = 100, 50
        col_count = 0
        max_cols = 3 
        
        for loc_key in sorted(locations.keys()): # Sort for consistent layout
            positions[loc_key] = (x, y)
            x += 150
            col_count += 1
            if col_count >= max_cols:
                col_count = 0
                x = 100
                y += 100
                
        return positions
