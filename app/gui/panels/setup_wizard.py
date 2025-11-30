import json
import logging
import random
import threading
import tkinter.messagebox

import customtkinter as ctk

from app.gui.styles import Theme
from app.models.prompt import Prompt
from app.models.stat_block import StatBlockTemplate
from app.setup.schemas import CharacterExtraction, WorldExtraction
from app.setup.world_gen_service import WorldGenService
from app.tools.schemas import MemoryUpsert

logger = logging.getLogger(__name__)


class SetupWizard(ctk.CTkToplevel):
    """
    A multi-step wizard for pre-game extraction.
    Steps:
    1. Concept Input (Text)
    2. Processing (LLM Extraction)
    3. Review & Edit (JSON/Forms)
    """

    def __init__(
        self, parent, db_manager, orchestrator, prompt: Prompt, session_manager
    ):
        super().__init__(parent)
        self.db = db_manager
        self.orchestrator = orchestrator
        self.prompt = prompt
        self.session_manager = session_manager

        self.title(f"New Game: {prompt.name}")
        self.geometry("1000x700")
        self.resizable(True, True)

        # Data State
        self.step = 0
        self.input_world_text = ""
        self.input_char_text = ""

        # Extracted Data (populated in Step 2)
        self.extracted_char: CharacterExtraction | None = None
        self.extracted_world: WorldExtraction | None = None
        self.generated_opening: str = ""

        # UI Containers
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Navigation Bar
        self.nav_frame = ctk.CTkFrame(self, height=50)
        self.nav_frame.pack(fill="x", side="bottom", padx=20, pady=20)

        self.back_btn = ctk.CTkButton(
            self.nav_frame, text="Back", command=self._prev_step, state="disabled"
        )
        self.back_btn.pack(side="left")

        self.next_btn = ctk.CTkButton(
            self.nav_frame, text="Next", command=self._next_step
        )
        self.next_btn.pack(side="right")

        # Make modal and render
        self.transient(parent)
        self.grab_set()
        self.lift()
        self.focus_force()

        # Safe Render
        self.after(10, self._render_current_step)

    def _render_current_step(self):
        """Clear container and render the current step's UI."""
        try:
            for widget in self.main_container.winfo_children():
                widget.destroy()

            if self.step == 0:
                self._render_step_input()
                self.back_btn.configure(state="disabled")
                self.next_btn.configure(
                    text="Generate", state="normal", command=self._start_extraction
                )
            elif self.step == 1:
                self._render_step_processing()
                self.back_btn.configure(state="disabled")
                self.next_btn.configure(state="disabled")  # Wait for process
            elif self.step == 2:
                self._render_step_review()
                self.back_btn.configure(state="normal")
                self.next_btn.configure(
                    text="Start Game", state="normal", command=self._finish
                )
        except Exception as e:
            logger.error(f"Error rendering wizard step {self.step}: {e}", exc_info=True)
            ctk.CTkLabel(
                self.main_container, text=f"Error rendering UI: {e}", text_color="red"
            ).pack()

    def _prev_step(self):
        if self.step > 0:
            self.step -= 1
            self._render_current_step()

    def _next_step(self):
        self.step += 1
        self._render_current_step()

    def _start_extraction(self):
        """Transition to processing step."""
        # Save inputs
        if hasattr(self, "world_input"):
            self.input_world_text = self.world_input.get("1.0", "end-1c")
        if hasattr(self, "char_input"):
            self.input_char_text = self.char_input.get("1.0", "end-1c")

        self.step = 1
        self._render_current_step()
        # Trigger background thread
        threading.Thread(target=self._run_extraction_thread, daemon=True).start()

    def _finish(self):
        """Commit data and launch game."""
        # 1. Finalize Lore Parsing (from the text box)
        if hasattr(self, "text_lore"):
            lore_text = self.text_lore.get("1.0", "end-1c")
            lines = [line.strip() for line in lore_text.split("\n") if line.strip()]

            # Convert lines back to MemoryUpsert objects
            new_lore = []
            for line in lines:
                new_lore.append(
                    MemoryUpsert(
                        kind="lore", content=line, priority=3, tags=["world_gen"]
                    )
                )
            if self.extracted_world:
                self.extracted_world.lore = new_lore

        # 2. Get Opening Crawl Settings
        generate_crawl = (
            bool(self.var_generate_crawl.get())
            if hasattr(self, "var_generate_crawl")
            else True
        )
        # Note: generated_opening might be empty if the user unchecked the box before step 2,
        # but we allow them to toggle it off here too.

        # 3. Pass to Session Manager
        self.session_manager.create_session_from_wizard(
            self.prompt,
            self.extracted_char,
            self.extracted_world,
            self.generated_opening,
            generate_crawl=generate_crawl,
        )
        self.destroy()

    # --- STEP RENDERERS ---

    def _render_step_input(self):
        """Step 1: Concept Input."""
        # Header
        header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            header_frame, text=f"Setup: {self.prompt.name}", font=Theme.fonts.heading
        ).pack(side="left")

        # Split Pane
        split_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        split_frame.pack(fill="both", expand=True)

        # --- LEFT: WORLD ---
        world_frame = ctk.CTkFrame(split_frame)
        world_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ctk.CTkLabel(
            world_frame, text="🌐 The World", font=Theme.fonts.subheading
        ).pack(pady=10)

        ctk.CTkLabel(
            world_frame,
            text="Describe the setting, atmosphere, and starting scenario.\nExample: 'Cyberpunk Tokyo, raining. Player starts in a ramen shop.'",
            text_color="gray",
            wraplength=400,
        ).pack(pady=(0, 10))

        self.world_input = ctk.CTkTextbox(world_frame)
        self.world_input.pack(fill="both", expand=True, padx=10, pady=10)
        self.world_input.insert("1.0", self.input_world_text)

        ctk.CTkButton(
            world_frame,
            text="🎲 Randomize World",
            command=self._randomize_world,
            fg_color="transparent",
            border_width=1,
        ).pack(pady=10)

        # --- RIGHT: CHARACTER ---
        char_frame = ctk.CTkFrame(split_frame)
        char_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))

        ctk.CTkLabel(
            char_frame, text="🎭 The Protagonist", font=Theme.fonts.subheading
        ).pack(pady=10)

        # POLISH: Dynamic System Hint
        hint_text = (
            "Describe your character. Mention their role, history, and strengths."
        )

        try:
            if self.prompt.template_manifest and self.prompt.template_manifest != "{}":
                data = json.loads(self.prompt.template_manifest)
                if "stat_template" in data:
                    t = data["stat_template"]
                    # Extract stats for hint
                    abilities = [a["name"] for a in t.get("abilities", [])]
                    if abilities:
                        hint_text += f"\n\nSystem: {t.get('template_name', 'Custom')}"
                        hint_text += f"\nKey Stats: {', '.join(abilities)}"
        except Exception as e:
            logger.warning(f"Failed to parse template manifest for hints: {e}")
            pass

        ctk.CTkLabel(
            char_frame, text=hint_text, text_color="gray", wraplength=400
        ).pack(pady=(0, 10))

        self.char_input = ctk.CTkTextbox(char_frame)
        self.char_input.pack(fill="both", expand=True, padx=10, pady=10)
        self.char_input.insert("1.0", self.input_char_text)

        ctk.CTkButton(
            char_frame,
            text="🎲 Randomize Character",
            command=self._randomize_char,
            fg_color="transparent",
            border_width=1,
        ).pack(pady=10)

    def _randomize_world(self):
        """Fill world input with a random preset."""
        presets = [
            "A crumbling gothic castle during a thunderstorm. The player wakes up in the dungeons with no memory.",
            "Neon-lit streets of Neo-Veridia. Acid rain falls. The player is a courier holding a package that ticks.",
            "A quiet village on the edge of the Whispering Woods. It is the day of the Harvest Festival.",
        ]
        self.world_input.delete("1.0", "end")
        self.world_input.insert("1.0", random.choice(presets))

    def _randomize_char(self):
        """Fill char input with a random preset."""
        presets = [
            "Kael, a disgraced knight seeking redemption. Strong and tough, but haunted by his past. Carries a broken sword.",
            "Vex, a street urchin with quick fingers and a quicker wit. High agility, uses a dagger. Has a pet rat named Squeaks.",
            "Elara, a scholar of the arcane. Intelligent but frail. Carries a spellbook and a staff.",
        ]
        self.char_input.delete("1.0", "end")
        self.char_input.insert("1.0", random.choice(presets))

    def _render_step_processing(self):
        """Step 2: Loading Screen."""
        self.lbl_processing = ctk.CTkLabel(
            self.main_container,
            text="Initializing Extraction...",
            font=Theme.fonts.heading,
        )
        self.lbl_processing.pack(expand=True)
        self.progress = ctk.CTkProgressBar(self.main_container)
        self.progress.pack(fill="x", padx=50)
        self.progress.start()

    def _render_step_review(self):
        """Step 3: Review Data."""
        self.geometry("500x700")
        ctk.CTkLabel(
            self.main_container, text="Step 3: Review & Edit", font=Theme.fonts.heading
        ).pack(pady=10)

        tabview = ctk.CTkTabview(self.main_container)
        tabview.pack(fill="both", expand=True)

        # --- TAB 1: CHARACTER ---
        tab_char = tabview.add("Character")

        # Name & Bio
        char_scroll = ctk.CTkScrollableFrame(tab_char, fg_color="transparent")
        char_scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(char_scroll, text="Name:", anchor="w").pack(fill="x")
        self.entry_name = ctk.CTkEntry(char_scroll)
        self.entry_name.pack(fill="x", pady=(0, 5))
        self.entry_name.insert(0, self.extracted_char.name)
        # Bind update back to model
        self.entry_name.bind(
            "<KeyRelease>",
            lambda _: setattr(self.extracted_char, "name", self.entry_name.get()),
        )

        ctk.CTkLabel(char_scroll, text="Visual Description:", anchor="w").pack(fill="x")
        self.text_vis = ctk.CTkTextbox(char_scroll, height=60)
        self.text_vis.pack(fill="x", pady=(0, 5))
        self.text_vis.insert("1.0", self.extracted_char.visual_description)
        self.text_vis.bind(
            "<KeyRelease>",
            lambda _: setattr(
                self.extracted_char,
                "visual_description",
                self.text_vis.get("1.0", "end-1c"),
            ),
        )

        # Stats Editor (Dynamic)
        ctk.CTkLabel(
            char_scroll,
            text="Stats (Inferred):",
            font=Theme.fonts.subheading,
            anchor="w",
        ).pack(fill="x", pady=5)

        self.stats_frame = ctk.CTkFrame(char_scroll)
        self.stats_frame.pack(fill="x", pady=5)

        self.stat_entries = {}
        row = 0
        for key, val in self.extracted_char.suggested_stats.items():
            ctk.CTkLabel(self.stats_frame, text=key).grid(
                row=row, column=0, padx=5, pady=2, sticky="e"
            )
            entry = ctk.CTkEntry(self.stats_frame)
            entry.grid(row=row, column=1, padx=5, pady=2, sticky="ew")
            entry.insert(0, str(val))
            # Bind updates to dictionary
            # Capture key=key to avoid closure binding issue
            entry.bind(
                "<KeyRelease>",
                lambda _, k=key, ent=entry: self._update_stat(k, ent.get()),
            )
            self.stat_entries[key] = entry
            row += 1
        self.stats_frame.grid_columnconfigure(1, weight=1)

        # Inventory
        ctk.CTkLabel(
            char_scroll, text="Inventory (One item per line):", anchor="w"
        ).pack(fill="x", pady=5)
        self.text_inv = ctk.CTkTextbox(char_scroll, height=100)
        self.text_inv.pack(fill="x")
        inv_text = "\n".join(self.extracted_char.inventory)
        self.text_inv.insert("1.0", inv_text)
        self.text_inv.bind("<KeyRelease>", self._update_inventory)

        # --- TAB 2: WORLD ---
        tab_world = tabview.add("World")

        world_scroll = ctk.CTkScrollableFrame(tab_world, fg_color="transparent")
        world_scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(
            world_scroll,
            text="Starting Location:",
            font=Theme.fonts.subheading,
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(world_scroll, text="Name:", anchor="w").pack(fill="x")
        self.entry_loc_name = ctk.CTkEntry(world_scroll)
        self.entry_loc_name.pack(fill="x", pady=(0, 5))
        self.entry_loc_name.insert(
            0, self.extracted_world.starting_location.name_display
        )
        self.entry_loc_name.bind(
            "<KeyRelease>",
            lambda _: setattr(
                self.extracted_world.starting_location,
                "name_display",
                self.entry_loc_name.get(),
            ),
        )

        ctk.CTkLabel(world_scroll, text="Visual Description (Card):", anchor="w").pack(
            fill="x"
        )
        self.text_loc_vis = ctk.CTkTextbox(world_scroll, height=80)
        self.text_loc_vis.pack(fill="x", pady=(0, 5))
        self.text_loc_vis.insert(
            "1.0", self.extracted_world.starting_location.description_visual
        )
        self.text_loc_vis.bind(
            "<KeyRelease>",
            lambda _: setattr(
                self.extracted_world.starting_location,
                "description_visual",
                self.text_loc_vis.get("1.0", "end-1c"),
            ),
        )

        ctk.CTkLabel(world_scroll, text="Lore Facts (One per line):", anchor="w").pack(
            fill="x", pady=5
        )
        self.text_lore = ctk.CTkTextbox(world_scroll, height=150)
        self.text_lore.pack(fill="x")
        lore_text = "\n".join([m.content for m in self.extracted_world.lore])
        self.text_lore.insert("1.0", lore_text)

        # --- TAB 3: OPENING ---
        tab_opening = tabview.add("Opening")

        # Controls
        controls_frame = ctk.CTkFrame(tab_opening, fg_color="transparent")
        controls_frame.pack(fill="x", padx=5, pady=5)

        self.var_generate_crawl = ctk.BooleanVar(value=True)
        self.check_gen = ctk.CTkCheckBox(
            controls_frame,
            text="Use Opening Narration",
            variable=self.var_generate_crawl,
            command=self._toggle_opening_text,
        )
        self.check_gen.pack(side="left")

        # Text Area
        self.text_opening = ctk.CTkTextbox(tab_opening, font=Theme.fonts.body)
        self.text_opening.pack(fill="both", expand=True, padx=5, pady=5)
        self.text_opening.insert("1.0", self.generated_opening)

        self.text_opening.bind(
            "<KeyRelease>",
            lambda e: setattr(
                self, "generated_opening", self.text_opening.get("1.0", "end-1c")
            ),
        )

    def _toggle_opening_text(self):
        """Enable/Disable the opening text box based on checkbox."""
        if self.var_generate_crawl.get():
            self.text_opening.configure(
                state="normal", fg_color=Theme.colors.bg_secondary
            )
        else:
            self.text_opening.configure(
                state="disabled", fg_color=Theme.colors.bg_tertiary
            )

    def _update_stat(self, key, value):
        """Update stat in extracted model, handling type conversion if possible."""
        try:
            # Try to keep int if it was int
            if value.isdigit():
                self.extracted_char.suggested_stats[key] = int(value)
            else:
                self.extracted_char.suggested_stats[key] = value
        except Exception:
            pass

    def _update_inventory(self, event):
        """Parse inventory lines back into list."""
        text = self.text_inv.get("1.0", "end-1c")
        items = [line.strip() for line in text.split("\n") if line.strip()]
        self.extracted_char.inventory = items

    def _run_extraction_thread(self):
        """Background logic for running the extraction pipeline."""
        try:
            connector = self.orchestrator._get_llm_connector()
            service = WorldGenService(connector)

            # 1. Parse Template from Prompt
            stat_template = None
            try:
                if (
                    self.prompt.template_manifest
                    and self.prompt.template_manifest != "{}"
                ):
                    data = json.loads(self.prompt.template_manifest)
                    if "stat_template" in data:
                        stat_template = StatBlockTemplate(**data["stat_template"])
            except Exception as e:
                logger.warning(f"Failed to parse template manifest: {e}")

            # Fallback if no template
            if not stat_template:
                from app.setup.scaffolding import _get_default_scaffolding

                _, stat_template = _get_default_scaffolding()

            # 2. Run Extractions
            self.after(
                0,
                lambda: self.lbl_processing.configure(
                    text="Extracting World Context..."
                ),
            )
            logger.info("Wizard: Extracting World...")
            self.extracted_world = service.extract_world_data(self.input_world_text)

            self.after(
                0, lambda: self.lbl_processing.configure(text="Analyzing Character...")
            )
            logger.info("Wizard: Extracting Character...")
            self.extracted_char = service.extract_character_data(
                self.input_char_text, stat_template
            )

            self.after(
                0,
                lambda: self.lbl_processing.configure(text="Writing Opening Scene..."),
            )
            logger.info("Wizard: Generating Opening...")
            # Extract Scenario Guidance (implicit from World Input for now, or added as step 1 field?)
            # For now, we treat the raw input as the guidance context.
            guidance = self.input_world_text  # Simple pass-through of the concept text

            self.generated_opening = service.generate_opening_crawl(
                self.extracted_char, self.extracted_world, guidance
            )

            # Transition
            self.after(0, lambda: self._on_extraction_complete())

        except Exception as e:
            logger.error(f"Wizard Extraction Failed: {e}", exc_info=True)
            err_msg = str(e)
            self.after(0, lambda: self._on_extraction_error(err_msg))

    def _on_extraction_complete(self):
        self.step = 2
        self._render_current_step()

    def _on_extraction_error(self, error_msg):
        # Simple error state
        self.step = 0  # Go back
        self._render_current_step()
        tkinter.messagebox.showerror("Generation Failed", f"AI Error: {error_msg}")
