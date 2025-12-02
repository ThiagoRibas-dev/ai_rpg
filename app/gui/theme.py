from nicegui import ui


class Theme:
    # Colors (Tailwind classes or Hex)
    bg_primary = "bg-slate-900"
    bg_secondary = "bg-slate-800"
    bg_tertiary = "bg-slate-700"

    text_primary = "text-gray-100"
    text_secondary = "text-gray-300"
    text_accent = "text-amber-400"  # Gold

    # Standard Spacing
    padding = "p-4"
    gap = "gap-4"

    @staticmethod
    def apply_global_styles():
        """Injects global CSS for scrollbars and font."""
        ui.add_head_html("""
            <style>
                body { background-color: #0f172a; color: #f3f4f6; }
                /* Custom Scrollbar */
                ::-webkit-scrollbar { width: 8px; }
                ::-webkit-scrollbar-track { background: #1e293b; }
                ::-webkit-scrollbar-thumb { background: #475569; border-radius: 4px; }
                ::-webkit-scrollbar-thumb:hover { background: #64748b; }
            </style>
        """)

    @staticmethod
    def header():
        return ui.header().classes(
            "bg-slate-950 border-b border-slate-800 h-16 items-center px-4"
        )

    @staticmethod
    def drawer_left():
        return ui.left_drawer(value=True).classes(
            "bg-slate-900 border-r border-slate-800 w-80 p-0"
        )

    @staticmethod
    def drawer_right():
        return ui.right_drawer(value=True).classes(
            "bg-slate-900 border-l border-slate-800 w-80 p-0"
        )
