import json

from app.tools.registry import ToolRegistry


def test_location_create_schema():
    registry = ToolRegistry()
    schemas = registry.get_llm_tool_schemas(["location.create"])

    assert len(schemas) == 1
    location_schema = schemas[0]["function"]

    # Check if 'location_type' is in the parameters
    params = location_schema["parameters"]["properties"]
    required = location_schema["parameters"]["required"]

    print("\nGenerated LocationCreate Schema Parameters:")
    print(json.dumps(params, indent=2))
    print("\nRequired Fields:", required)

    assert "location_type" in params
    assert "location_type" in required
    assert params["location_type"]["type"] == "string"

if __name__ == "__main__":
    test_location_create_schema()
    print("\nVerification successful: Schema contains 'location_type' as required.")
