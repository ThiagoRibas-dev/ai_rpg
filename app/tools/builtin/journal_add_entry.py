from typing import Any

def handler(
    title: str,
    content: str,
    tags: list[str] = None,
    is_secret: bool = False,
    **context: Any
) -> dict:
    """
    Handler for journal.add_entry.
    Stores the entry as a 'semantic' memory with special tags for filtering.
    """
    session_id = context["session_id"]
    db = context["db_manager"]
    
    # We use the existing Memory table but tag it specially
    final_tags = tags or []
    final_tags.append("journal")
    if is_secret:
        final_tags.append("secret")
    
    # Prefix content with Title for searchability
    formatted_content = f"JOURNAL: {title}\n{content}"
    
    memory = db.memories.create(
        session_id=session_id,
        kind="semantic", # or create a new 'journal' kind if DB allows
        content=formatted_content,
        priority=4,
        tags=final_tags
    )

    return {
        "success": True,
        "journal_id": memory.id,
        "title": title
    }

