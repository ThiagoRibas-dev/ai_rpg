# AI-RPG Architecture Flows

This document contains Mermaid diagrams illustrating the main application flows of the AI-RPG system.

## System Overview

```mermaid
graph TB
    subgraph UI_Layer["UI Layer (NiceGUI)"]
        Chat[Chat Component]
        Map[Map Component]
        Inspector[Inspector Manager]
        SessionList[Session List]
    end

    subgraph Core_Layer["Core Layer"]
        Orchestrator[Orchestrator]
        TurnManager[ReActTurnManager]
    end

    subgraph Services_Layer["Services Layer"]
        ContextBuilder[ContextBuilder]
        ToolExecutor[ToolExecutor]
        StateBuilder[StateContextBuilder]
        MemoryRetriever[MemoryRetriever]
        SimulationService[SimulationService]
    end

    subgraph Storage_Layer["Storage Layer"]
        SQLite[(SQLite Database)]
        VectorStore[(ChromaDB Vector Store)]
    end

    subgraph External_Layer["External Services"]
        LLM[LLM Provider<br/>Gemini/OpenAI]
    end

    Chat -->|User Input| Orchestrator
    Map -->|State Query| SQLite
    Inspector -->|State Display| SQLite
    SessionList -->|Session Management| SQLite
    
    Orchestrator --> TurnManager
    TurnManager --> ContextBuilder
    TurnManager --> ToolExecutor
    TurnManager --> SimulationService
    
    ContextBuilder --> StateBuilder
    ContextBuilder --> MemoryRetriever
    ContextBuilder --> SQLite
    ContextBuilder --> VectorStore
    
    ToolExecutor -->|Execute Tools| SQLite
    ToolExecutor -->|Update State| SQLite
    ToolExecutor -->|Memory Ops| VectorStore
    
    TurnManager -->|Chat Requests| LLM
    SimulationService -->|Streaming| LLM
    
    SQLite <-->|FTS / Query| MemoryRetriever
    VectorStore <-->|Semantic Search| MemoryRetriever
```

## Turn Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as UI Thread (NiceGUI)
    participant Orch as Orchestrator
    participant TM as ReActTurnManager
    participant CB as ContextBuilder
    participant MR as MemoryRetriever
    participant DB as SQLite Database
    participant VS as Vector Store
    participant LLM as LLM Provider
    participant TE as ToolExecutor

    User->>UI: Submit user message
    UI->>Orch: plan_and_execute(session, message)
    Orch->>Orch: Add message to session history
    Orch->>UI: Show user message bubble
    Orch->>UI: Emit PLANNING_STARTED event
    Orch->>TM: execute_turn(game_session, db_manager, turn_id)
    
    Note over TM,CB: Phase 1: Context Assembly
    TM->>TM: Load SystemManifest from DB
    TM->>CB: build_static_system_instruction()
    CB->>DB: Fetch manifest rules
    TM->>CB: build_dynamic_context()
    CB->>DB: Fetch entity index
    CB->>DB: Fetch active quests
    CB->>DB: Fetch current scene
    CB->>DB: Fetch character sheet
    TM->>MR: get_relevant(active_tags)
    MR->>DB: Search BM25 (FTS)
    MR->>VS: Search Semantic
    MR->>MR: RRF Fusion & Reranking
    MR-->>TM: Return relevant memories
    
    Note over TM,LLM: Phase 2: ReAct Loop
    loop Max 15 iterations
        TM->>LLM: chat_with_tools(system_prompt, history, tools)
        LLM-->>TM: Response with thought + tool_calls
        
        alt Has tool_calls
            TM->>UI: Emit THOUGHT_BUBBLE event
            TM->>TE: execute(tool_calls, context)
            TE->>DB: Read/Write game state
            TE-->>TM: Return tool results
            TM->>UI: Emit TOOL_RESULT event
            TM->>TM: Append tool result to history
        else No tool_calls
            TM->>TM: Break loop
        end
    end
    
    Note over TM,LLM: Phase 3: Final Narrative
    TM->>LLM: get_streaming_response(narrative)
    LLM-->>TM: Narrative text
    
    Note over TM,LLM: Phase 4: Post-Processing
    TM->>LLM: get_structured_response(suggestions)
    LLM-->>TM: Return choices
    TM->>UI: Emit CHOICES event
    
    Note over TM,DB: Phase 5: Persistence
    TM->>DB: Update session state
    TM->>VS: Persist turn metadata
    TM->>UI: Emit TURN_COMPLETE event
```

## ReAct Loop Detail

```mermaid
graph TB
    subgraph ReAct["ReAct Loop (Max 15 iterations)"]
        Start([Start Loop])
        CheckStop{Stop Event<br/>Set?}
        LLMCall[LLM: chat_with_tools]
        HasThought{Has Thought?}
        HasTools{Has Tool Calls?}
        
        Think[LLM generates thought]
        SelectTool[LLM selects atomic tool]
        ExecuteTool[ToolExecutor.execute]
        UpdateHistory[Update working history]
        
        CheckDone{Narrative<br/>Generated?}
        End([End Loop])
    end

    Start --> CheckStop
    CheckStop -->|Yes| End
    CheckStop -->|No| LLMCall
    LLMCall --> HasThought
    HasThought -->|Yes| Think
    HasThought -->|No| HasTools
    Think --> HasTools
    HasTools -->|Yes| SelectTool
    HasTools -->|No| CheckDone
    SelectTool --> ExecuteTool
    ExecuteTool --> UpdateHistory
    UpdateHistory --> CheckStop
    CheckDone -->|No| LLMCall
    CheckDone -->|Yes| End
```

## Tool Execution Flow

```mermaid
graph TB
    subgraph ToolRegistry["ToolRegistry"]
        ToolList[Registered Tools]
        SchemaGen[Generate LLM Schemas]
    end

    subgraph ToolExecutor["ToolExecutor"]
        Validate[Validate Args]
        Dispatch[Dispatch Handler]
        PostHook[Post-Hook / UI Events]
    end

    subgraph Handlers["Tool Handlers"]
        direction TB
        ReadDB[(Read State)]
        
        subgraph Logic["Logic & Validation"]
            direction TB
            Adjust[adjust]
            Set_[set]
            Roll[roll]
            Mark[mark]
            Move[move]
            Note[note]
            ContextRet["context.retrieve"]
            StateQuery["state.query"]
            NpcSpawn["npc.spawn"]
            LocCreate["location.create"]
            
            subgraph Validation["Validation Pipeline"]
                Formulas["Recalculate Formulas"]
                Clamp["Clamp Values"]
                Invariants["Check Invariants"]
            end
        end
        
        WriteDB[(Write State)]
    end

    subgraph Storage["External Storage"]
        DB[(SQLite)]
        VS[(Vector Store)]
    end

    LLMCall[LLM Tool Call] --> Validate
    Validate --> Dispatch
    Dispatch --> ToolList
    ToolList --> HandlerSelect{Select Handler}
    
    HandlerSelect --> ReadDB
    ReadDB -.-> DB
    
    ReadDB --> Logic
    Logic --> Validation
    Validation --> WriteDB
    
    WriteDB -.-> DB
    WriteDB -.-> VS
    
    WriteDB --> PostHook
```

## Context Building Flow

```mermaid
graph TB
    subgraph StaticContext["Static Context Assembly"]
        Persona[Core Persona]
        Rules[Game System Rules]
        AuthorsNote[Author's Note]
    end

    subgraph DynamicContext["Dynamic Context Assembly"]
        EntityIndex[Entity Index]
        Quests[Active Quests]
        Scene[Current Scene]
        Character[Character Sheet]
    end

    subgraph RAG["RAG Integration"]
        direction TB
        MemoryRet[Memory Retriever]
        
        subgraph HybridSearch["Hybrid Search"]
            direction LR
            FTS[SQLite FTS / BM25]
            Semantic[Vector Semantic]
        end
        
        RRF[RRF Fusion]
        Rerank[Cross-Encoder Reranking]
        Budget[Budgeting & Formatting]

        MemoryRet --> HybridSearch
        HybridSearch --> RRF
        RRF --> Rerank
        Rerank --> Budget
        Budget --> DynamicContext
    end

    subgraph Manifest["Manifest System"]
        ManifestData[SystemManifest]
        EngineConfig[Engine Configuration]
        PrefabRules[Prefab Usage Rules]
    end

    StaticContext --> Prompt[Final System Prompt]
    DynamicContext --> Prompt
    RAG --> Prompt

    Persona --> Prompt
    Rules --> ManifestData
    AuthorsNote --> Prompt

    EntityIndex --> DynamicContext
    Quests --> DynamicContext
    Scene --> DynamicContext
    Character --> ManifestData

    ManifestData --> EngineConfig
    ManifestData --> PrefabRules
    EngineConfig --> Rules
    PrefabRules --> Rules
```

## UI Event Flow

```mermaid
sequenceDiagram
    participant BG as Background Thread
    participant Q as UI Queue
    participant UI as UI Thread
    participant Comp as UI Components

    BG->>Q: put(PLANNING_STARTED)
    Q->>UI: process_queue()
    UI->>Comp: Emit planning indicator

    BG->>Q: put(MESSAGE_BUBBLE, user)
    Q->>UI: process_queue()
    UI->>Comp: Render user message

    BG->>Q: put(THOUGHT_BUBBLE)
    Q->>UI: process_queue()
    UI->>Comp: Show AI thinking

    BG->>Q: put(TOOL_CALL)
    Q->>UI: process_queue()
    UI->>Comp: Show tool call

    BG->>Q: put(DICE_ROLL)
    Q->>UI: process_queue()
    UI->>Comp: Animate dice roll

    BG->>Q: put(TOOL_RESULT)
    Q->>UI: process_queue()
    UI->>Comp: Show tool result

    BG->>Q: put(STATE_CHANGED)
    Q->>UI: process_queue()
    UI->>Comp: Refresh inspectors

    BG->>Q: put(CHOICES)
    Q->>UI: process_queue()
    UI->>Comp: Display suggestion buttons

    BG->>Q: put(TURN_COMPLETE)
    Q->>UI: process_queue()
    UI->>Comp: Clear planning indicator
```

## Data Persistence Flow

```mermaid
graph TB
    subgraph TurnEnd["Turn Completion"]
        SessionState[Session State]
        History[Message History]
        Metadata[Turn Metadata]
    end

    subgraph SQLite["SQLite Database"]
        Sessions[sessions Table]
        GameState[game_state Table]
        Manifests[manifests Table]
        Memories[memories Table]
        TurnMeta[turn_metadata Table]
    end

    subgraph Vector["ChromaDB Vector Store"]
        MemoryIndex[Memory Index]
        RuleIndex[Rule Index]
        TurnIndex[Turn Metadata Index]
    end

    SessionState --> Sessions
    History --> Sessions
    GameState --> GameState
    Metadata --> TurnMeta

    Sessions -->|Update| SQLite
    GameState -->|Update| SQLite
    TurnMeta -->|Update| SQLite

    Memories --> MemoryIndex
    RuleIndex --> RuleIndex
    Metadata --> TurnIndex

    MemoryIndex -->|Embed| Vector
    RuleIndex -->|Embed| Vector
    TurnIndex -->|Embed| Vector
```

## Component Responsibilities

```mermaid
graph TB
    subgraph Orchestrator["Orchestrator"]
        MainController[Main Controller]
        ThreadMgmt[Thread Management]
        EventBridge[Event Bridge]
        LLMInit[LLM Connector Init]
        ToolReg[Tool Registry Init]
    end

    subgraph TurnManager["ReActTurnManager"]
        ManifestLoad[Load Manifest]
        ContextBuild[Build Context]
        ReActLoop[Execute ReAct Loop]
        NarrativeGen[Generate Narrative]
        Suggestions[Generate Suggestions]
        Persistence[Persist State]
        Chronicler[Background Chronicler]
    end

    subgraph ContextBuilder["ContextBuilder"]
        StaticPrompt[Static Prompt]
        DynamicPrompt[Dynamic Prompt]
        EntityIndex[Entity Index]
        SceneBuilder[Scene Builder]
        CharacterBuilder[Character Builder]
    end

    subgraph ToolExecutor["ToolExecutor"]
        ToolDispatch[Tool Dispatch]
        StateOps[State Operations]
        MemoryOps[Memory Operations]
        UIEvents[UI Event Emission]
    end

    subgraph StateBuilder["StateContextBuilder"]
        Quests[Quests]
        SceneRoster[Scene Roster]
        CharacterSheet[Character Sheet]
        WorldIndex[World Index]
    end

    subgraph MemoryRetriever["MemoryRetriever"]
        HybridSearch[Hybrid Search: FTS + Semantic]
        RRFFusion[RRF Rank Fusion]
        Reranking[Cross-Encoder Reranking]
        Deduplication[Episodic Deduplication]
        Budgeting[Budgeting & Formatting]
    end

    MainController --> TurnManager
    ThreadMgmt --> TurnManager
    EventBridge --> TurnManager
    LLMInit --> TurnManager
    ToolReg --> TurnManager

    TurnManager --> ContextBuilder
    TurnManager --> ToolExecutor
    TurnManager --> StateBuilder
    TurnManager --> MemoryRetriever

    ContextBuilder --> StaticPrompt
    ContextBuilder --> DynamicPrompt
    ContextBuilder --> EntityIndex
    ContextBuilder --> SceneBuilder
    ContextBuilder --> CharacterBuilder

    ToolExecutor --> ToolDispatch
    ToolExecutor --> StateOps
    ToolExecutor --> MemoryOps
    ToolExecutor --> UIEvents

    StateBuilder --> Quests
    StateBuilder --> SceneRoster
    StateBuilder --> CharacterSheet
    StateBuilder --> WorldIndex

    MemoryRetriever --> HybridSearch
    MemoryRetriever --> RRFFusion
    MemoryRetriever --> Reranking
    MemoryRetriever --> Deduplication
    MemoryRetriever --> Budgeting
```
