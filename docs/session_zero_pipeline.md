# Session Zero Generation Pipeline

The two top-level pipelines (`WorldGenService` and `SheetGenerator`) run in **parallel** via `asyncio.gather` in the `SetupWizard`. They coordinate via the `LoreStream` object passed to both.

```mermaid
flowchart TD

    subgraph Wizard["SetupWizard._execute_pipeline (asyncio.gather)"]
        direction LR
        WG["WorldGenService"]
        CG["SheetGenerator"]
    end

    subgraph WorldGen["WorldGenService.async_extract_world_data"]
        direction TB
        W0["GENRE\n(Genre & Tone extraction)"]
        W1["INDEX\n(Master Deep Scan)"]

        subgraph W2["Layer 2 - Parallel Batch Extraction (asyncio.gather)"]
            direction LR
            WA["ATLAS\n(Locations)"]
            WB["DRAMATIS\n(NPCs)"]
            WC["CODEX\n(Systems Lore)"]
            WD["PEOPLES\n(Races Lore)"]
            WE["POWER\n(Factions Lore)"]
            WF["CHRONICLE\n(History Lore)"]
            WG2["CULTURE\n(Culture Lore)"]
            WH["REMNANTS\n(Misc Lore)"]
        end

        W3["ASSEMBLY\n(Combine all results)"]
        W4["OPENING CRAWL\n(async_generate_opening_crawl)"]

        W0 --> W1
        W1 --> W2
        W2 --> W3
        W3 --> W4
    end

    subgraph CharGen["SheetGenerator.async_generate_from_manifest"]
        direction TB

        subgraph CB1["Batch 1 (Sequential)"]
            direction LR
            B1A["BASE\n(Identity, Race, Class)"]
        end

        subgraph CB2["Batch 2 (Sequential after Batch 1)"]
            direction LR
            B2A["MECHANICS\n(Stats, Skills, Combat)"]
        end

        subgraph CB3["Batch 3 (Parallel, Sequential after Batch 2)"]
            direction LR
            B3A["DERIVED\n(Calculated fields)"]
            B3B["BACKGROUND\n(History, Connections)\n⏳ Waits for NPC data"]
        end

        CB1 --> CB2 --> CB3
    end

    %% Cross-pipeline NPC dependency
    WB -- "stream.set_npcs()\n(fulfills asyncio.Future)" --> B3B

    WG --> WorldGen
    CG --> CharGen
```

## Key Design Notes

| Concept | Detail |
|---|---|
| **Top-level parallelism** | World gen and Char gen run concurrently via `asyncio.gather` in the wizard |
| **World gen: Layer 0 & 1** | Genre extraction and the Deep Scan/Index run **sequentially** — the index depends on the genre context |
| **World gen: Layer 2** | All category batches (Locations, NPCs, Lore variants) run **in parallel** via `asyncio.gather` |
| **NPC fulfillment** | As soon as the NPC batch result arrives (before all of Layer 2 finishes), `stream.set_npcs()` is called to unblock chargen |
| **Chargen batches** | Batches are sequential (each waits for the previous), but branches *within* a batch run in parallel |
| **Background branch** | Waits on `await stream.get_npcs()` — an `asyncio.Future` that yields the loop until fulfilled |
| **Error propagation** | If world gen fails, `stream.set_error(e)` is called, which causes the `Background` branch to raise immediately rather than hang |
