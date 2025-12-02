from nicegui import ui
from app.gui.theme import Theme
import asyncio

class ChatComponent:
    def __init__(self, orchestrator, bridge, session_manager):
        self.orchestrator = orchestrator
        self.bridge = bridge
        self.session_manager = session_manager
        self.container = None
        self.input_area = None
        self.scroll_area = None
        
        self.bridge.register_chat(self)

    def render(self):
        # Message Area
        with ui.scroll_area().classes('w-full flex-grow p-4 gap-4') as area:
            self.container = ui.column().classes('w-full gap-4') # Increased gap
            self.scroll_area = area
            
            with self.container:
                self.add_message("System", "Ready. Load a session to begin.", "system")

        # Input Area
        with ui.row().classes('w-full p-4 ' + Theme.bg_tertiary + ' items-end border-t border-slate-700'):
            self.input_area = ui.textarea(placeholder='What do you do?') \
                .props('autogrow rows=1 rounded outlined input-class="text-white"') \
                .classes('w-full text-lg') \
                .on('keydown.enter.prevent', self.handle_enter)

            ui.button(icon='send', on_click=self.handle_enter) \
                .props('flat round dense') \
                .classes(Theme.text_accent)

    def load_history(self):
        if not self.container: return
        self.container.clear()
        
        session = self.orchestrator.session
        if not session: return

        with self.container:
            for msg in session.history:
                name = "AI"
                if msg.role == "user": name = "You"
                elif msg.role == "system": name = "System"
                
                if msg.role == "tool": continue # Skip raw tool results
                self.add_message(name, msg.content, msg.role)
        
        self._scroll_down()

    def add_message(self, name: str, text: str, role: str):
        if not self.container: return
        if not text: text = "..."

        with self.container:
            sent = (role == 'user')
            
            # Message Styling
            if role == 'thought':
                with ui.row().classes('w-full justify-start'):
                    with ui.card().classes('bg-yellow-900/20 border border-yellow-700/50 p-2'):
                        ui.label("💭 Thinking...").classes('text-xs text-yellow-500 font-bold mb-1')
                        ui.markdown(text).classes('text-sm text-yellow-200 italic')
            
            elif role == 'system':
                with ui.row().classes('w-full justify-center'):
                    ui.label(text).classes('text-gray-500 italic text-sm')
            
            else:
                # Standard Chat Message
                msg = ui.chat_message(name=name, sent=sent)
                with msg:
                    ui.markdown(text).classes('text-base leading-relaxed')
        
        self._scroll_down()

    def add_tool_log(self, name: str, args: dict):
        """Render a collapsible debug log for tool usage."""
        if not self.container: return
        
        with self.container:
            with ui.row().classes('w-full justify-start'):
                # Compact visualization
                with ui.expansion(f"🛠 {name}", icon='code').classes('w-full max-w-lg bg-slate-900 border border-slate-800 rounded text-xs'):
                    ui.json(args).classes('text-xs text-green-400 p-2')
        
        self._scroll_down()

    def add_dice_roll(self, spec: str, total: int, rolls: list):
        """Render a visual Dice Card."""
        if not self.container: return
        
        # Color logic
        is_crit = total >= 20
        is_fail = total == 1
        border = 'border-slate-600'
        text_col = 'text-white'
        
        if is_crit: 
            border = 'border-green-500 shadow-lg shadow-green-900/50'
            text_col = 'text-green-400'
        elif is_fail:
            border = 'border-red-500'
            text_col = 'text-red-400'

        with self.container:
            with ui.row().classes('w-full justify-center'):
                with ui.card().classes(f'bg-slate-800 {border} border-2 p-4 items-center min-w-[200px]'):
                    ui.label(f"Rolled {spec}").classes('text-xs text-gray-400 uppercase font-bold')
                    ui.label(str(total)).classes(f'text-4xl font-black {text_col}')
                    
                    if len(rolls) > 1:
                        ui.label(f"Results: {rolls}").classes('text-xs text-gray-500')

        self._scroll_down()

    def add_choices(self, choices: list):
        """Render clickable action buttons."""
        if not self.container or not choices: return
        
        with self.container:
            with ui.column().classes('w-full items-center gap-2 p-4 bg-slate-900/50 rounded border border-slate-700'):
                ui.label("Suggested Actions").classes('text-xs font-bold text-gray-500 uppercase')
                
                with ui.row().classes('flex-wrap justify-center gap-2'):
                    for choice in choices:
                        ui.button(choice, on_click=lambda c=choice: self.handle_choice(c)) \
                            .classes('bg-slate-700 hover:bg-slate-600 text-white text-sm')

        self._scroll_down()

    def handle_choice(self, text):
        self.input_area.value = text
        self.handle_enter()

    def handle_enter(self):
        text = self.input_area.value
        if not text.strip(): return

        self.input_area.value = ''
        self.add_message("You", text, "user")
        self.bridge._last_input = text
        
        if self.orchestrator.session:
            game_session = self.session_manager.get_active_session()
            if game_session:
                self.orchestrator.plan_and_execute(game_session)
            else:
                ui.notify("Session state mismatch", type="negative")
        else:
            ui.notify("No session loaded!", type="warning")

    def _scroll_down(self):
        if self.scroll_area:
            self.scroll_area.scroll_to(percent=1.0)