import math

# 1. Define the JSON schema for the tool
schema = {
    "name": "math.eval",
    "description": "Evaluates a simple mathematical expression.",
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The mathematical expression to evaluate (e.g., '2+3*4')."
            }
        },
        "required": ["expression"]
    }
}

# 2. Implement the handler function
def handler(expression: str) -> float:
    """
    Evaluates a simple mathematical expression.
    
    For safety, this implementation only allows basic math operations.
    A more robust implementation would use a dedicated parsing library.
    """
    allowed_chars = "0123456789+-*/(). "
    if not all(char in allowed_chars for char in expression):
        raise ValueError("Expression contains invalid characters.")
    
    try:
        # Using eval() is a security risk, but for this controlled environment
        # with character validation, it's a simple starting point.
        return eval(expression, {"__builtins__": None}, {"math": math})
    except Exception as e:
        raise ValueError(f"Invalid mathematical expression: {expression}") from e
