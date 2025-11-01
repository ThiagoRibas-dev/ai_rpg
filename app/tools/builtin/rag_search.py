from typing import Any

schema = {
    "name": "rag.search",
    "description": "Retrieve short lore chunks for flavor. Timebox at caller.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "k": {"type": "integer"},
            "filters": {"type": "object", "additionalProperties": True}
        },
        "required": ["query"]
    }
}

def handler(query: str, k: int = 2, filters: dict[str, Any] | None = None, **context) -> dict:
    # MVP stub: return empty or canned examples
    chunks = []
    if "ambush" in query.lower():
        chunks = [
            {"id": "lore:bandit_tactics", "text": "Bush-side decoy rustle; attackers wait off-angle.", "score": 0.82, "meta": {"topic": "ambush"}},
            {"id": "lore:small_game", "text": "Small game make erratic, low rustles unlike human weight shifts.", "score": 0.61, "meta": {"topic": "wildlife"}},
        ]
    return {"chunks": chunks[:k]}