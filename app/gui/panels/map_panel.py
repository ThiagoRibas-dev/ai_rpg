import math
import customtkinter as ctk
from typing import Dict, Any, Optional
from app.tools.builtin._state_storage import get_entity # Reuse existing helper
from app.gui.styles import Theme

class MapPanel(ctk.CTkFrame):
    """
    Visualizes game space in two modes:
    1. World Graph (Nodes & Edges)
    2. Tactical Grid (Algebraic A1, B2...)
    """

    def __init__(self, parent, db_manager, **kwargs):
        super().__init__(parent, **kwargs)
        self.db_manager = db_manager
        self.session_id: Optional[int] = None
        
        self.mode = "tactical" # or "world"
        
        # Controls
        self.controls = ctk.CTkFrame(self, height=30, fg_color="transparent")
        self.controls.pack(fill="x", padx=5, pady=5)
        
        self.mode_btn = ctk.CTkSegmentedButton(
            self.controls, 
            values=["Tactical", "World"],
            command=self.set_mode
        )
        self.mode_btn.set("Tactical")
        self.mode_btn.pack(side="left")
        
        self.refresh_btn = ctk.CTkButton(
            self.controls,
            text="⬇️",
            width=30,
            command=self.refresh
        )
        self.refresh_btn.pack(side="right")

        # Canvas
        self.canvas = ctk.CTkCanvas(
            self, 
            bg=Theme.colors.bg_secondary, 
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        # State
        self.grid_size = 40 # Pixels per cell
        self.world_data = {}
        self.tactical_data = {}

        # Bind resize
        self.canvas.bind("<Configure>", self.redraw)

    def set_session(self, session_id: int):
        """Sets the current session ID."""
        self.session_id = session_id
        # Auto-refresh when session is set
        self.refresh()

    def refresh(self):
        """
        Loads the latest map state from the database.
        Called by SessionManager on load.
        """
        if not self.session_id or not self.db_manager:
            return

        try:
            # Fetch Active Scene for Tactical Data
            scene = get_entity(self.session_id, self.db_manager, "scene", "active_scene")
            if scene and "tactical_map" in scene:
                tmap = scene["tactical_map"]
                # Convert DB format {positions: {key: coord}} to UI format {entities: {coord: key}}
                ui_entities = {}
                if "positions" in tmap:
                    for key, coord in tmap["positions"].items():
                        ui_entities[coord] = key
                
                self.tactical_data = {
                    "width": tmap.get("width", 5),
                    "height": tmap.get("height", 5),
                    "terrain": tmap.get("terrain", {}),
                    "entities": ui_entities
                }
            
            # Fetch Location for World Data
            if scene and "location_key" in scene:
                loc_key = scene["location_key"]
                location = get_entity(self.session_id, self.db_manager, "location", loc_key)
                if location:
                    self.update_world(loc_key, location.get("connections", {}))

            self.redraw()
        except Exception as e:
            print(f"Error refreshing map: {e}")

    def set_mode(self, mode: str):
        self.mode = mode.lower()
        self.redraw()

    def update_tactical(self, map_data: Dict[str, Any]):
        """
        Updates the tactical grid directly (from Tool Output).
        """
        self.tactical_data = map_data
        if self.mode == "tactical":
            self.redraw()

    def update_world(self, current_location_key: str, connections: Dict[str, Any]):
        """
        Updates the world graph.
        """
        self.world_data = {
            "center": current_location_key,
            "neighbors": connections # { "north": {"target_key": "hall"} }
        }
        if self.mode == "world":
            self.redraw()

    def redraw(self, event=None):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        
        if self.mode == "tactical":
            self._draw_tactical(w, h)
        else:
            self._draw_world(w, h)

    def _draw_tactical(self, w, h):
        cols = self.tactical_data.get("width", 5)
        rows = self.tactical_data.get("height", 5)
        entities = self.tactical_data.get("entities", {})
        terrain = self.tactical_data.get("terrain", {})
        
        # Center the grid
        grid_w = cols * self.grid_size
        grid_h = rows * self.grid_size
        start_x = (w - grid_w) // 2
        start_y = (h - grid_h) // 2

        # Draw Grid
        for r in range(rows):
            for c in range(cols):
                x1 = start_x + c * self.grid_size
                y1 = start_y + (rows - 1 - r) * self.grid_size # Flip Y so 1 is bottom
                x2 = x1 + self.grid_size
                y2 = y1 + self.grid_size
                
                # Coord string (e.g., "A1")
                col_char = chr(65 + c)
                row_num = r + 1
                coord = f"{col_char}{row_num}"
                
                # Draw Cell
                fill = "#2b2b2b"
                if coord in terrain:
                    fill = "#4a4a4a" # Wall/Obstacle
                
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="gray30", fill=fill)
                
                # Draw Coordinate Label (faint)
                self.canvas.create_text(
                    x1 + 5, y2 - 5, 
                    text=coord, 
                    fill="gray40", 
                    font=("Arial", 8),
                    anchor="sw"
                )

                # Draw Entity
                if coord in entities:
                    char_key = entities[coord]
                    # Simple representation: First letter or symbol
                    symbol = "@" if "player" in char_key else char_key.split(":")[-1][0].upper()
                    color = Theme.colors.text_gold if "player" in char_key else "#ff6b6b"
                    
                    self.canvas.create_text(
                        (x1+x2)//2, (y1+y2)//2,
                        text=symbol,
                        fill=color,
                        font=("Arial", 16, "bold")
                    )

    def _draw_world(self, w, h):
        center_x, center_y = w // 2, h // 2
        radius = 100
        
        current = self.world_data.get("center", "Unknown")
        neighbors = self.world_data.get("neighbors", {})
        
        # Draw Center Node
        self._draw_node(center_x, center_y, current, fill=Theme.colors.text_gold)
        
        # Draw Neighbors
        if not neighbors:
            return

        angle_step = 360 / len(neighbors)
        for i, (direction, data) in enumerate(neighbors.items()):
            angle_rad = math.radians(i * angle_step - 90) # Start top
            nx = center_x + radius * math.cos(angle_rad)
            ny = center_y + radius * math.sin(angle_rad)
            
            # Draw Edge
            self.canvas.create_line(center_x, center_y, nx, ny, fill="gray50", width=2)
            
            # Draw Label on Line
            self.canvas.create_text(
                (center_x + nx) // 2, (center_y + ny) // 2,
                text=direction.upper(),
                fill="gray80",
                font=("Arial", 9),
                tags="bg_text"
            )
            
            # Draw Node
            name = data.get("display_name", "???")
            is_locked = data.get("is_locked", False)
            color = "#555" if is_locked else "#3a7ebf"
            self._draw_node(nx, ny, name, fill=color)

    def _draw_node(self, x, y, text, fill):
        r = 30
        self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=fill, outline="white")
        self.canvas.create_text(x, y, text=text[:10], fill="white", font=("Arial", 10, "bold"))
