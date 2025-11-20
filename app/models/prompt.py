from dataclasses import dataclass


@dataclass
class Prompt:
    id: int
    name: str
    content: str
    rules_document: str = ""
    template_manifest: str = "{}"
