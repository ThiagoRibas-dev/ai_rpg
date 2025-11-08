from datetime import datetime, timezone

def handler(**context) -> dict:
    return {"iso8601": datetime.now(timezone.utc).isoformat()}
