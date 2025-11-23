"""
Handles UI queue processing and message routing.

New responsibilities:
- Poll UI queue on main thread
- Route messages to appropriate handlers
- Coordinate loading states, choices, inspector refreshes
- Update game time/mode labels
"""

import queue
import logging
from typing import Dict, Any
import customtkinter as ctk
from app.gui.utils.ui_helpers import create_choice_buttons, get_mode_display

logger = logging.getLogger(__name__)


class UIQueueHandler:
    """
    Processes messages from the orchestrator's UI queue.
    """

    def __init__(
        self,
        orchestrator,
        bubble_manager,
        tool_viz_manager,
        loading_frame: ctk.CTkFrame,
        loading_label: ctk.CTkLabel,
        choice_button_frame: ctk.CTkFrame,
        send_button: ctk.CTkButton,
        game_time_label: ctk.CTkLabel,
        game_mode_label: ctk.CTkLabel,
        navigation_frame: ctk.CTkFrame,
        inspectors: Dict[str, Any],
        map_panel: Any, # Assuming MapPanel is passed
    ):
        """
        Initialize the UI queue handler.

        Args:
            orchestrator: Orchestrator instance
            bubble_manager: ChatBubbleManager instance
            tool_viz_manager: ToolVisualizationManager instance
            loading_frame: Loading indicator frame
            loading_label: Loading indicator label
            choice_button_frame: Frame for action choice buttons
            send_button: Send button to enable/disable
            game_time_label: Label for game time updates
            game_mode_label: Label for game mode updates
            navigation_frame: Frame for navigation buttons
            inspectors: Dictionary of inspector instances
        """
        self.orchestrator = orchestrator
        self.bubble_manager = bubble_manager
        self.tool_viz_manager = tool_viz_manager
        self.loading_frame = loading_frame
        self.loading_label = loading_label
        self.choice_button_frame = choice_button_frame
        self.send_button = send_button
        self.game_time_label = game_time_label
        self.game_mode_label = game_mode_label
        self.navigation_frame = navigation_frame
        self.inspectors = inspectors
        self.map_panel = map_panel # Store reference to MapPanel

        # Callback for choice selection (set externally by MainView)
        self.on_choice_selected = None

    def start_polling(self):
        """
        Start polling the UI queue.
        """
        self._process_queue()

    def _process_queue(self):
        """
        Process messages from the orchestrator's UI queue.
        """
        try:
            processed = 0
            while True:  # Process all pending messages
                msg = self.orchestrator.ui_queue.get_nowait()
                self._handle_message(msg)
                processed += 1
        except queue.Empty:
            pass
        finally:
            if processed > 0:
                logger.debug(f"Processed {processed} UI messages")
            # Re-schedule polling
            # Use orchestrator's view for after() call
            self.orchestrator.view.after(100, self._process_queue)

    def _handle_message(self, msg: Dict[str, Any]):
        """
        Handle a single UI message from the orchestrator.

        Message routing table:
        - thought_bubble → bubble_manager.add_message
        - message_bubble → bubble_manager.add_message
        - tool_call → tool_viz_manager.add_tool_call
        - tool_result → tool_viz_manager.add_tool_result
        - choices → create_choice_buttons (ui_helpers)
        - error → bubble_manager.add_message (as system)
        - turn_complete → inspectors refresh + enable send button
        - refresh_memory_inspector → memory_inspector.refresh_memories
        - update_game_time → game_time_label update
        - update_game_mode → game_mode_label update

        Args:
            msg: Message dictionary with 'type' and type-specific fields
        """
        msg_type = msg.get("type")
        logger.debug(f"UI message received: {msg_type}")

        # ---Handle the planning_started message ---
        # This message is sent right before the first LLM call.
        if msg_type == "planning_started":
            self.loading_label.configure(text=msg.get("content", "AI is thinking..."))
            self.loading_frame.grid(
                row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5
            )
        # === Thought Bubble ===
        elif msg_type == "thought_bubble":
            # The loading frame is now shown by the 'planning_started' message,
            # so we no longer need to show it here.
            self.bubble_manager.add_message("thought", msg["content"])

        # === Message Bubble ===
        elif msg_type == "message_bubble":
            # self.add_message_bubble → self.bubble_manager.add_message
            self.bubble_manager.add_message(msg["role"], msg["content"])

        # === Tool Call ===
        elif msg_type == "tool_call":
            logger.debug(
                f"Processing tool_call: {msg.get('name')} with args: {msg.get('args')}"
            )
            # self.add_tool_call → self.tool_viz_manager.add_tool_call
            try:
                self.tool_viz_manager.add_tool_call(msg["name"], msg["args"])
                logger.debug("Tool call added to visualization")
            except Exception as e:
                logger.error(f"Failed to add tool call to panel: {e}", exc_info=True)

        # === Tool Result ===
        elif msg_type == "tool_result":
            # self.add_tool_result → self.tool_viz_manager.add_tool_result
            self.tool_viz_manager.add_tool_result(
                msg["result"], msg.get("is_error", False)
            )

            # Special Handling: Location Change event from tool result
            if (
                isinstance(msg["result"], dict)
                and msg["result"].get("ui_event") == "location_change"
            ):
                loc_data = msg["result"].get("location_data", {})
                self.bubble_manager.add_location_card(loc_data)

                # Clear navigation until next turn refresh
                for widget in self.navigation_frame.winfo_children():
                    widget.destroy()
        
        # === Tactical Map Update ===
        elif msg_type == "map_update":
            if self.map_panel:
                raw_data = msg["data"]
                # The tool sends {key: coord}, UI expects {coord: key}
                ui_entities = {v: k for k, v in raw_data["entities"].items()}
                ui_data = {
                    "width": raw_data["width"],
                    "height": raw_data["height"],
                    "terrain": raw_data["terrain"],
                    "entities": ui_entities
                }
                self.map_panel.update_tactical(ui_data)

        # === NEW: Dice Roll ===
        elif msg_type == "dice_roll":
            # Route to the new visual card instead of a text bubble
            self.bubble_manager.add_dice_card(msg)

        # === Choices ===
        elif msg_type == "choices":
            if self.on_choice_selected:
                # self.display_action_choices → create_choice_buttons (ui_helpers)
                create_choice_buttons(
                    self.choice_button_frame, msg["choices"], self.on_choice_selected
                )

        # === Error ===
        elif msg_type == "error":
            # self.add_message_bubble → self.bubble_manager.add_message
            self.bubble_manager.add_message("system", f"Error: {msg['message']}")

        # === Turn Complete ===
        elif msg_type == "turn_complete":
            self.loading_frame.grid_remove()  # Hide loading
            self.send_button.configure(state="normal")  # Re-enable

            # Refresh inspectors if needed
            # Direct inspector access → via inspectors dict
            if "character" in self.inspectors and self.inspectors["character"]:
                self.inspectors["character"].refresh()
            if "inventory" in self.inspectors and self.inspectors["inventory"]:
                self.inspectors["inventory"].refresh()
            if "quest" in self.inspectors and self.inspectors["quest"]:
                self.inspectors["quest"].refresh()
            if "map" in self.inspectors and self.inspectors["map"]:
                self.inspectors["map"].refresh()
            if "scene_map" in self.inspectors and self.inspectors["scene_map"]:
                self.inspectors["scene_map"].refresh()

        # === Update Navigation ===
        elif msg_type == "update_nav":
            # Clear old buttons
            for widget in self.navigation_frame.winfo_children():
                widget.destroy()

            exits = msg.get("exits", [])
            if exits:
                ctk.CTkLabel(
                    self.navigation_frame, text="Exits:", font=("Arial", 12, "bold")
                ).pack(side="left", padx=5)
                for exit_name in exits:
                    btn = ctk.CTkButton(
                        self.navigation_frame,
                        text=exit_name,
                        width=60,
                        command=lambda e=exit_name: self._send_nav_command(e),
                    )
                    btn.pack(side="left", padx=2, pady=2)

        # === Refresh Memory Inspector ===
        elif msg_type == "refresh_memory_inspector":
            if "memory" in self.inspectors and self.inspectors["memory"]:
                self.inspectors["memory"].refresh_memories()

        # === Update Game Time ===
        elif msg_type == "update_game_time":
            self.game_time_label.configure(text=f"{msg['new_time']}")

        # === Update Game Mode ===
        elif msg_type == "update_game_mode":
            # self._get_mode_display → get_mode_display (ui_helpers)
            mode_text, mode_color = get_mode_display(msg["new_mode"])
            self.game_mode_label.configure(text=mode_text, text_color=mode_color)

        # === Tool Event (Legacy) ===
        elif msg_type == "tool_event":
            logger.info(f"Tool Event: {msg['message']}")
            # Optionally display this in a specific debug area or log

        # === Unknown Message Type ===
        else:
            logger.warning(f"Unknown UI message type: {msg_type}")

    def _send_nav_command(self, direction: str):
        """Injects a move command into the input."""
        # We need reference to input_manager, or hack it via orchestrator/view
        # Ideally UIQueueHandler shouldn't do this, but for MVP:
        if self.orchestrator.view:
            self.orchestrator.view.input_manager.handle_choice_selected(
                f"I go {direction}"
            )
