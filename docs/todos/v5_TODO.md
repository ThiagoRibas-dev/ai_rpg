# AI RPG v5 Upgrades TODO

This document tracks the implementation of the v5 upgrades for the AI RPG, focusing on enhanced memory management, improved orchestration, and semantic retrieval.

- [x] **Create `docs/todos/v5_TODO.md`**: Create a new TODO file to track the implementation of these upgrades.
- [x] **`app/core/vector_store.py`**: Extend `VectorStore` to manage new collections for `memories` and `world_info`, including methods for upserting, deleting, and searching.
- [x] **`app/tools/schemas.py`**: Add the `semantic` flag to the `MemoryQuery` schema to enable semantic search mode.
- [x] **`app/tools/builtin/memory_upsert.py`**: Modify the `memory.upsert` tool to automatically embed new memories in the vector store.
- [x] **`app/tools/builtin/memory_update.py`**: Modify the `memory.update` tool to update the corresponding embeddings.
- [x] **`app/tools/builtin/memory_delete.py`**: Modify the `memory.delete` tool to remove memories from the vector store.
- [x] **`app/tools/builtin/memory_query.py`**: Enhance the `memory.query` tool to perform semantic searches and blend the results with existing filters.
- [x] **`app/tools/registry.py`**: Implement near-duplicate detection in the `ToolRegistry` to automatically convert `memory.upsert` calls into `memory.update` when appropriate.
- [x] **`app/core/orchestrator.py`**: Implement multiple enhancements:
    - [x] Integrate `VectorStore` into the tool execution context.
    - [x] Fuse semantic search results in `_get_relevant_memories`.
    - [x] Replace keyword world info retrieval with semantic RAG.
    - [x] Update `PLAN_TEMPLATE` and `NARRATIVE_TEMPLATE` with the new guided questions and guardrails.
    - [x] Implement the consistency audit, tool budget, and procedural memory optimization.
- [x] **`app/io/schemas.py`**: Define the `AuditResult` schema for the new consistency audit step.
- [x] **`app/gui/world_info_manager_view.py`**: Update the World Info Manager to embed/update world info entries in the vector store when they are created, saved, or deleted.
- [x] **`app/gui/main_view.py`**: Pass the `vector_store` instance to the `WorldInfoManagerView`.
