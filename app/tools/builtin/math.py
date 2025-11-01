import re

schema = {
    "name": "math.eval",
    "description": "Evaluates a simple mathematical expression (+ - * / ( )).",
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Math expression, e.g., '2+3*4'"
            }
        },
        "required": ["expression"]
    }
}

_allowed = re.compile(r"^[0-9+\-*/().\s]+$")

def handler(expression: str, **context) -> dict:
    if not _allowed.match(expression):
        raise ValueError("Expression contains invalid characters.")
    try:
        value = eval(expression, {"__builtins__": None}, {})
        return {"value": float(value)}
    except Exception as e:
        raise ValueError(f"Invalid mathematical expression: {expression}") from e