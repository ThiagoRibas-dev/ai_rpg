from nicegui import ui


class Theme:
    # Colors (Tailwind classes or Hex)
    bg_primary = "bg-slate-900"
    bg_secondary = "bg-slate-800"
    bg_tertiary = "bg-slate-700"

    text_primary = "text-gray-100"
    text_secondary = "text-gray-300"
    text_accent = "text-amber-400"  # Gold

    # Chat Specific Colors - consistent with dark slate theme
    chat_bubble_sent = "bg-emerald-700 text-white"
    chat_bubble_received = "bg-slate-800 text-gray-200 border border-slate-700"

    # Standard Spacing
    padding = "p-4"
    gap = "gap-4"

    @staticmethod
    def apply_global_styles():
        """Injects global CSS for scrollbars and font."""
        ui.add_head_html("""
            <style>
                body { background-color: #0f172a; color: #f3f4f6; overflow: hidden; }
                ::-webkit-scrollbar-thumb { background: #475569; border-radius: 4px; }
                ::-webkit-scrollbar-thumb:hover { background: #64748b; }

                /* Chat Bubble Constraints */
                .q-message-label { max-width: 100%; }
                .q-message-text { max-width: 100%; word-break: break-word; }
                .q-message-content { max-width: 100%; }

                /* Force Markdown Code Blocks to Wrap */
                pre, code {
                    white-space: pre-wrap !important;
                    word-wrap: break-word !important;
                    max-width: 100%;
                }

                /* Compact Chat Markdown */
                .chat-markdown {
                    line-height: 1.4 !important;
                    text-align: justify !important;
                }
                .chat-markdown h1, .chat-markdown h2, .chat-markdown h3, .chat-markdown p, .chat-markdown li {
                    white-space: pre-wrap !important;
                }
                .chat-markdown h1 { font-size: 2rem !important; font-weight: bold; margin: 8px 0 4px 0 !important;  }
                .chat-markdown h2 { font-size: 1.8rem !important; font-weight: bold; margin: 8px 0 4px 0 !important;  }
                .chat-markdown h3 { font-size: 1.6rem !important; font-weight: bold; margin: 6px 0 3px 0 !important;  }
                .chat-markdown p { margin-bottom: 6px !important; }
                .chat-markdown p:last-child { margin-bottom: 0 !important; }
                .chat-markdown ul, .chat-markdown ol { margin: 4px 0 !important; padding-left: 1.5rem !important; }
                .chat-markdown li { margin-bottom: 2px !important; }
                .chat-markdown blockquote {
                    border-left: 3px solid #475569;
                    padding-left: 10px;
                    font-italic: italic;
                    margin: 4px 0 !important;
                }
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
