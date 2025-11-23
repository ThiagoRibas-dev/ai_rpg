### Phase 1: Map & Tool Logic (The Foundation)
*   [ ] **Refactor `LocationCreate` Schema** (`app/tools/schemas.py`)
    *   Add a `neighbors` list field (containing `target_key` and `direction`) to the schema.
*   [ ] **Update `location.create` Handler** (`app/tools/builtin/location_create.py`)
    *   Implement logic to iterate through `neighbors`.
    *   Automatically create bidirectional connections (graph edges) when a new location is created.
*   [ ] **Update `WorldExtraction` Schema** (`app/setup/schemas.py`)
    *   Add a `neighbors` list to the extraction model so the AI generates adjacent rooms/areas immediately during setup.
*   [ ] **Update Prompts** (`app/prompts/templates.py`)
    *   Update `WORLD_EXTRACTION_PROMPT`: Instruct AI to generate the starting location **AND** 2-3 immediate neighbors with narrative connections.
    *   Add **Granularity Instructions**: Explicitly tell the AI to create locations at the "Room/Building" scale, not "Furniture" scale.

### Phase 2: Wizard & Setup Enhancements
*   [x] **Update `SetupWizard` UI** (`app/gui/panels/setup_wizard.py`)
    *   [x] **Step 3**: Add a Checkbox: `[x] Generate Opening Narration` (Default: Checked).
    *   [x] **Step 3**: Add a Textbox: `Initial Scenario Guidance` (e.g., "Start in combat", "I am sleeping").
*   [x] **Update `WorldGenService`** (`app/setup/world_gen_service.py`)
    *   [x] Modify `generate_opening_crawl` to accept the optional `scenario_guidance` string and inject it into the prompt.
*   [x] **Update `SessionManager` Creation Logic** (`app/gui/managers/session_manager.py`)
    *   [x] **Persist Initial State**: Save the raw `CharacterExtraction` and `WorldExtraction` JSON data into `session.setup_phase_data` (this is required for Cloning).
    *   [x] **Handle Neighbors**: Loop through the extracted `neighbors` and call `location.create` for them during initialization.
    *   [x] **Handle Crawl Toggle**:
        *   [x] If **ON**: Generate text and add as the first Assistant message.
        *   [x] If **OFF**: Skip generation. Insert a system marker ("Session initialized at [Location]").

### Phase 3: Session Management UI
*   [x] **Add "Edit" Functionality** (`app/gui/managers/session_manager.py`)
    *   [x] Add a "Rename" (pencil) button to the session list rows.
    *   [x] Implement a simple dialog to rename the session in the database.
*   [x] **Add "Clone" Functionality** (`app/gui/managers/session_manager.py`)
    *   [x] Add a "Clone" (copy) button to the session list rows.
    *   [x] **Implement Cloning Logic**:
        1.  Load source session.
        2.  Extract the saved `initial_state` (from Phase 2).
        3.  Create a new Session record.
        4.  **Link Ruleset**: Reuse the existing `ruleset_id` and `stat_template_id` (do not duplicate the system).
        5.  **Re-apply State**: Run the setup logic (create player, locations, lore) using the saved extraction data.
