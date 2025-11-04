from pydantic import BaseModel, ConfigDict

class SchemaModel(BaseModel):
    # your global defaults for all schemas
    model_config = ConfigDict(
        title=None,
        validation_error_cause=True,
        use_enum_values=True,     # serialize enums as their values (e.g., "modifier")
        # extra='forbid',           # reject unknown fields by default (optional)
        # populate_by_name=True,    # allow aliases if you use them (optional)
        # validate_assignment=False # toggle if you want assignment validation (optional)
    )