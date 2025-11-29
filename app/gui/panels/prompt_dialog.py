"""Prompt Dialog with Optimized Counting."""

import customtkinter as ctk
from app.gui.styles import Theme


class PromptDialog(ctk.CTkToplevel):
    def __init__(
        self, parent, title="New Prompt", existing_prompt=None, llm_connector=None
    ):
        super().__init__(parent)
        self.title(title)
        self.geometry("1024x720")
        self.result = None
        self.existing_prompt = existing_prompt
        self.llm_connector = llm_connector
        self._create_widgets()
        self._load_existing_data()
        self.transient(parent)
        self.grab_set()

    def _create_widgets(self):
        main = ctk.CTkScrollableFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(main, text="Name:", font=Theme.fonts.subheading).pack(fill="x")
        self.name_entry = ctk.CTkEntry(main)
        self.name_entry.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(main, text="System Prompt:", font=Theme.fonts.subheading).pack(
            fill="x"
        )
        self.content_textbox = ctk.CTkTextbox(main, height=200)
        self.content_textbox.pack(fill="both", expand=True, pady=(0, 15))

        ctk.CTkLabel(main, text="Rules Document:", font=Theme.fonts.subheading).pack(
            fill="x"
        )
        self.rules_textbox = ctk.CTkTextbox(main, height=200)
        self.rules_textbox.pack(fill="both", expand=True, pady=(0, 15))

        gen_frame = ctk.CTkFrame(main, fg_color="transparent")
        gen_frame.pack(fill="x", pady=(0, 15))
        self.generate_btn = ctk.CTkButton(
            gen_frame, text="Generate Template", command=self._generate
        )
        self.generate_btn.pack(side="left")
        self.gen_status = ctk.CTkLabel(gen_frame, text="", text_color="gray")
        self.gen_status.pack(side="left", padx=10)

        ctk.CTkLabel(main, text="Template JSON:", font=Theme.fonts.subheading).pack(
            fill="x"
        )
        self.template_textbox = ctk.CTkTextbox(main, height=200)
        self.template_textbox.pack(fill="both", expand=True, pady=(0, 15))

        btns = ctk.CTkFrame(main, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Cancel", command=self.destroy).pack(side="left")
        ctk.CTkButton(btns, text="Save", command=self._save).pack(side="right")

    def _generate(self):
        import threading

        rules = self.rules_textbox.get("1.0", "end-1c").strip()
        if not rules:
            return
        self.gen_status.configure(text="Generating...")
        self.generate_btn.configure(state="disabled")
        threading.Thread(target=self._gen_thread, args=(rules,), daemon=True).start()

    def _gen_thread(self, rules):
        try:
            from app.setup.template_generation_service import TemplateGenerationService

            gen = TemplateGenerationService(
                self.llm_connector, rules, lambda m: self.after(0, self._upd_status, m)
            )
            rs, st = gen.generate_template()
            self.after(
                0,
                self._on_gen,
                {"ruleset": rs.model_dump(), "stat_template": st.model_dump()},
                None,
            )
        except Exception as e:
            self.after(0, self._on_gen, None, str(e))

    def _upd_status(self, msg):
        self.gen_status.configure(text=msg)

    def _on_gen(self, data, err):
        self.generate_btn.configure(state="normal")
        if err:
            self.gen_status.configure(text=f"Error: {err}", text_color="red")
            return

        import json

        self.template_textbox.delete("1.0", "end")
        self.template_textbox.insert("1.0", json.dumps(data, indent=2))

        # Count Props (Dict based)
        count = 0
        rs = data.get("ruleset", {})
        count += len(rs.get("mechanics", {}))

        st = data.get("stat_template", {})
        count += len(st.get("fundamental_stats", {}))
        count += len(st.get("derived_stats", {}))
        count += len(st.get("vital_resources", {}))
        count += len(st.get("consumable_resources", {}))
        count += len(st.get("skills", {}))
        count += len(st.get("features", {}))
        count += len(st.get("equipment", {}).get("slots", {}))

        self.gen_status.configure(
            text=f"Generated {count} properties", text_color="green"
        )

    def _save(self):
        name = self.name_entry.get().strip()
        content = self.content_textbox.get("1.0", "end-1c").strip()
        rules = self.rules_textbox.get("1.0", "end-1c").strip()
        tpl = self.template_textbox.get("1.0", "end-1c").strip()
        if name and content:
            self.result = (name, content, rules, tpl)
            self.grab_release()
            self.destroy()

    def _load_existing_data(self):
        if self.existing_prompt:
            self.name_entry.insert(0, self.existing_prompt.name)
            self.content_textbox.insert("1.0", self.existing_prompt.content)
            self.rules_textbox.insert("1.0", self.existing_prompt.rules_document or "")
            self.template_textbox.insert(
                "1.0", self.existing_prompt.template_manifest or "{}"
            )

    def get_result(self):
        return self.result
