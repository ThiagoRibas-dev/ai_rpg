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

class NiceGUIBridge:
    def __init__(self):
        self.ui_queue = queue.Queue()
        self.chat_component = None
        self.inspector_component = None
        self.map_component = None
        self.session_name_label = MockElement()
        self._last_input = ""

    def register_chat(self, component): self.chat_component = component
    def register_inspector(self, component): self.inspector_component = component
    def register_map(self, component): self.map_component = component
    def register_header_label(self, label): self.session_name_label.ui_element = label

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
        
        if msg_type in ["message_bubble", "thought_bubble"]:
            if self.chat_component:
                role = "assistant" if msg_type == "message_bubble" else "thought"
                if "role" in msg: role = msg["role"]
                self.chat_component.add_message("AI", msg.get("content", ""), role)

        elif msg_type == "tool_call":
            if self.chat_component:
                self.chat_component.add_tool_log(msg.get('name'), msg.get('args'))

        elif msg_type == "dice_roll":
            if self.chat_component:
                self.chat_component.add_dice_roll(msg.get("spec"), msg.get("total"), msg.get("rolls"))

        elif msg_type == "choices":
            if self.chat_component:
                self.chat_component.add_choices(msg.get("choices", []))

        # Map Updates (Tactical)
        elif msg_type == "map_update":
            if self.map_component:
                # Backend sends {entities: {key: coord}}
                # UI expects {entities: {coord: key}} for rendering loop
                raw = msg.get("data", {})
                ui_entities = {v: k for k, v in raw.get("entities", {}).items()}
                
                ui_data = {
                    "width": raw.get("width", 5),
                    "height": raw.get("height", 5),
                    "terrain": raw.get("terrain", {}),
                    "entities": ui_entities
                }
                self.map_component.update_tactical(ui_data)

        # State Updates
        elif msg_type in ["turn_complete", "state_changed", "refresh_memory_inspector"]:
            if self.inspector_component: self.inspector_component.refresh()
            # Refresh map on turn complete too (to catch location changes)
            if self.map_component: self.map_component.refresh_from_db()

        elif msg_type == "error":
            if self.chat_component:
                self.chat_component.add_message("Error", msg.get('message'), "system")