from datetime import datetime, timezone

schema = {
    "name": "time.now",
    "description": "Return current ISO 8601 timestamp.",
    "parameters": {"type": "object", "properties": {}}
}

def handler() -> dict:
    return {"iso8601": datetime.now(timezone.utc).isoformat()}