import customtkinter as ctk

class CollapsibleFrame(ctk.CTkFrame):
    """
    A collapsible frame widget with a clickable header that toggles content visibility.
    """
    def __init__(self, parent, title: str, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.title = title
        self.is_collapsed = False
        
        # Header button
        self.header_button = ctk.CTkButton(
            self,
            text=f"▼ {self.title}",
            command=self.toggle,
            fg_color=("gray75", "gray25"),
            hover_color=("gray70", "gray30"),
            anchor="w"
        )
        self.header_button.pack(fill="x", padx=2, pady=2)
        
        # Content frame
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
    def toggle(self):
        """Toggle the visibility of the content frame."""
        if self.is_collapsed:
            self.content_frame.pack(fill="both", expand=True, padx=2, pady=2)
            self.header_button.configure(text=f"▼ {self.title}")
            self.is_collapsed = False
        else:
            self.content_frame.pack_forget()
            self.header_button.configure(text=f"▶ {self.title}")
            self.is_collapsed = True
            
    def get_content_frame(self):
        """Returns the content frame for adding widgets."""
        return self.content_frame