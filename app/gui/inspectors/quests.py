from nicegui import ui
from app.gui.theme import Theme
from app.tools.builtin._state_storage import get_all_of_type

class QuestInspector:
    def __init__(self, db_manager):
        self.db = db_manager
        self.session_id = None
        self.container = None

    def set_session(self, session_id: int):
        self.session_id = session_id
        self.refresh()

    def refresh(self):
        if not self.container:
            return
        self.container.clear()
        
        if not self.session_id:
            return

        quests = get_all_of_type(self.session_id, self.db, "quest")
        
        with self.container:
            if not quests:
                ui.label("No Active Quests").classes('text-gray-500 italic text-center w-full mt-4')
                return

            for key, quest in quests.items():
                self._render_quest_card(quest)

    def _render_quest_card(self, quest):
        status = quest.get('status', 'active')
        is_completed = status == 'completed'
        
        border_color = 'border-green-600' if is_completed else 'border-amber-500'
        icon = 'check_circle' if is_completed else 'star'
        
        with ui.card().classes(f'w-full bg-slate-800 border-l-4 {border_color} p-3 mb-2'):
            with ui.row().classes('w-full justify-between items-start'):
                with ui.column().classes('gap-1'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon(icon).classes(f'text-lg {"text-green-400" if is_completed else "text-amber-400"}')
                        ui.label(quest.get('title', 'Unknown Quest')).classes('font-bold text-md')
                    
                    ui.label(quest.get('description', '')).classes('text-sm text-gray-400')
                
                ui.badge(status.upper(), color='green' if is_completed else 'orange')

            # Objectives / Steps
            steps = quest.get('steps', [])
            if steps:
                ui.separator().classes('my-2 bg-slate-700')
                for step in steps:
                    with ui.row().classes('items-center gap-2 ml-2'):
                        chk = 'box-checked' if step.get('done') else 'box'
                        icon_chk = 'check_box' if step.get('done') else 'check_box_outline_blank'
                        ui.icon(icon_chk).classes('text-gray-500 text-xs')
                        ui.label(step.get('text', '')).classes('text-xs text-gray-300')