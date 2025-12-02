import queue
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class MockElement:
    def __init__(self, ui_element=None):
        self.ui_element = ui_element
    def configure(self, text=None, **kwargs):
        if self.ui_element and text is not None:
            self.ui_element.set_text(text)
    def set_text(self, text):
        if self.ui_element: self.ui_element.set_text(text)

class NiceGUIBridge:
    def __init__(self):
        self.ui_queue = queue.Queue()
        self.chat_component = None
        self.inspector_component = None
        self.map_component = None
        
        # Header Labels
        self.session_label = MockElement()
        self.time_label = MockElement()
        self.mode_label = MockElement()
        
        self._last_input = ""

    def register_chat(self, component): self.chat_component = component
    def register_inspector(self, component): self.inspector_component = component
    def register_map(self, component): self.map_component = component
    
    def register_header_labels(self, session_lbl, time_lbl, mode_lbl):
        self.session_label.ui_element = session_lbl
        self.time_label.ui_element = time_lbl
        self.mode_label.ui_element = mode_lbl

    # --- Interface ---
    def get_input(self) -> str: return self._last_input
    def clear_input(self): self._last_input = ""
    def mainloop(self): pass

    # --- Loop ---
    async def process_queue(self):
        try:
            while not self.ui_queue.empty():
                msg = self.ui_queue.get_nowait()
                await self._dispatch_message(msg)
        except Exception as e:
            logger.error(f"Error processing UI queue: {e}", exc_info=True)

    async def _dispatch_message(self, msg: Dict[str, Any]):
        msg_type = msg.get("type")
        
        # --- Chat & Interaction ---
        if msg_type in ["message_bubble", "thought_bubble"]:
            if self.chat_component:
                role = "assistant" if msg_type == "message_bubble" else "thought"
                if "role" in msg: role = msg["role"]
                self.chat_component.add_message("AI", msg.get("content", ""), role)

        elif msg_type == "tool_call":
            if self.chat_component:
                self.chat_component.add_tool_log(msg.get('name'), msg.get('args'))

        elif msg_type == "tool_result":
            result = msg.get("result", {})
            # Location Banner Logic
            if isinstance(result, dict) and result.get("ui_event") == "location_change":
                if self.chat_component:
                    self.chat_component.add_location_banner(result.get("location_data", {}))
                    self.chat_component.clear_navigation() 

        elif msg_type == "dice_roll":
            if self.chat_component:
                self.chat_component.add_dice_roll(msg.get("spec"), msg.get("total"), msg.get("rolls"))

        elif msg_type == "choices":
            if self.chat_component:
                self.chat_component.add_choices(msg.get("choices", []))

        elif msg_type == "update_nav":
            if self.chat_component:
                self.chat_component.update_navigation(msg.get("exits", []))

        # --- Visuals & State ---
        elif msg_type == "map_update":
            if self.map_component:
                raw = msg.get("data", {})
                ui_entities = {v: k for k, v in raw.get("entities", {}).items()}
                ui_data = {
                    "width": raw.get("width", 5),
                    "height": raw.get("height", 5),
                    "terrain": raw.get("terrain", {}),
                    "entities": ui_entities
                }
                self.map_component.update_tactical(ui_data)

        elif msg_type in ["turn_complete", "state_changed", "refresh_memory_inspector"]:
            if self.inspector_component: self.inspector_component.refresh()
            if self.map_component: self.map_component.refresh_from_db()
            if self.chat_component: self.chat_component.set_generating(False)

        elif msg_type == "planning_started":
            if self.chat_component: self.chat_component.set_generating(True)

        elif msg_type == "history_changed":
            if self.chat_component: self.chat_component.load_history()

        elif msg_type == "error":
            if self.chat_component:
                self.chat_component.add_message("Error", msg.get('message'), "system")
                self.chat_component.set_generating(False)

        # --- Header Updates ---
        elif msg_type == "update_game_time":
            self.time_label.set_text(msg.get("new_time", ""))
            
        elif msg_type == "update_game_mode":
            self.mode_label.set_text(msg.get("new_mode", ""))