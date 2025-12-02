from nicegui import ui
from app.gui.theme import Theme
from app.services.state_service import get_entity, get_versions

class CharacterInspector:
    def __init__(self, db_manager):
        self.db = db_manager
        self.session_id = None
        self.container = None
        self.entity_key = "player"

    def set_session(self, session_id: int):
        self.session_id = session_id
        self.refresh()

    def refresh(self):
        if not self.container:
            return
        
        self.container.clear()
        
        if not self.session_id:
            with self.container:
                ui.label("No Session Loaded").classes('text-gray-500 italic')
            return

        # Fetch Data
        entity = get_entity(self.session_id, self.db, "character", self.entity_key)
        if not entity:
            with self.container:
                ui.label("Player entity not found").classes('text-red-400')
            return

        # Fetch Template
        tid = entity.get("template_id")
        template = self.db.stat_templates.get_by_id(tid) if tid else None

        if not template:
            with self.container:
                ui.label("No Stat Template linked").classes('text-yellow-600')
            return

        # Render
        with self.container:
            self._render_header(entity)
            self._render_gauges(entity, template)
            self._render_stats_grid(entity, template)

    def _render_header(self, entity):
        with ui.row().classes('w-full items-center justify-between mb-4'):
            ui.label(entity.get('name', 'Unknown')).classes('text-2xl font-bold text-white')
            ui.chip(entity.get('disposition', 'Player'), icon='person').classes('bg-slate-700')

    def _render_gauges(self, entity, template):
        """Render HP, Mana, etc. as visual bars."""
        gauges_data = entity.get('gauges', {})
        
        # Filter template for gauges assigned to 'header' or 'main'
        # For this MVP, we render all gauges
        if not template.gauges:
            return

        with ui.card().classes('w-full bg-slate-800 p-2 mb-4 border-l-4 border-red-500'):
            ui.label('Vitals').classes('text-xs font-bold text-gray-400 uppercase mb-1')
            
            for key, def_ in template.gauges.items():
                data = gauges_data.get(key, {})
                curr = data.get('current', 0)
                mx = data.get('max', 10)
                
                # Prevent div by zero
                pct = max(0, min(1, curr / mx)) if mx > 0 else 0
                
                with ui.row().classes('w-full items-center gap-2'):
                    ui.label(def_.label).classes('w-20 text-sm')
                    with ui.column().classes('flex-grow gap-0'):
                        ui.linear_progress(value=pct, size='10px', show_value=False).classes('rounded')
                        ui.label(f"{curr} / {mx}").classes('text-xs text-center w-full text-gray-500')

    def _render_stats_grid(self, entity, template):
        """Render Attributes, Skills, etc using CSS Grid."""
        fundamentals = entity.get('fundamentals', {})
        derived = entity.get('derived', {})
        
        # Merge stats for display, keyed by Group
        groups = {}
        
        # Process Fundamentals
        for key, def_ in template.fundamentals.items():
            groups.setdefault(def_.group, []).append({**def_.model_dump(), 'value': fundamentals.get(key, def_.default)})
            
        # Process Derived
        for key, def_ in template.derived.items():
            groups.setdefault(def_.group, []).append({**def_.model_dump(), 'value': derived.get(key, def_.default)})

        # Render Groups
        for group_name, stats in groups.items():
            with ui.column().classes('w-full mb-4'):
                ui.label(group_name).classes('text-lg font-bold ' + Theme.text_accent)
                
                # CSS Grid: 2 Columns
                with ui.grid(columns=2).classes('w-full gap-2'):
                    for stat in stats:
                        self._render_stat_widget(stat)

    def _render_stat_widget(self, stat):
        """Decide how to draw a single stat based on its widget type."""
        widget_type = stat.get('widget', 'text')
        val = stat.get('value')
        
        with ui.card().classes('bg-slate-700 p-2 items-center flex-row justify-between'):
            ui.label(stat['label']).classes('text-sm text-gray-300')
            
            if widget_type == 'die':
                # Die Badge
                ui.badge(str(val), color='purple').props('text-color=white')
            
            elif widget_type == 'bonus':
                # +2 formatted text
                color = 'text-green-400' if int(val or 0) >= 0 else 'text-red-400'
                fmt = f"+{val}" if int(val or 0) >= 0 else str(val)
                ui.label(fmt).classes(f'text-xl font-bold {color}')
                
            elif widget_type == 'track':
                # Checkboxes
                # We assume 'max' is passed in rendering or defaulted
                length = 5 # Default fallback
                if 'rendering' in stat and stat['rendering']:
                     length = stat['rendering'].get('max', 5) # Simplify logic for MVP
                
                with ui.row().classes('gap-1'):
                    for i in range(length):
                        # Calculate if checked
                        is_checked = i < (int(val) if val else 0)
                        icon = 'check_box' if is_checked else 'check_box_outline_blank'
                        color = 'text-green-400' if is_checked else 'text-gray-600'
                        ui.icon(icon).classes(color)
            
            else:
                # Default Number/Text
                ui.label(str(val)).classes('text-lg font-mono')

    def render(self):
        # Create the container that refresh() will populate
        self.container = ui.column().classes('w-full p-2')
        self.refresh()