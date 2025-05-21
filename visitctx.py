from pydantic import BaseModel

class VisitContext(BaseModel):
    current_indent: int = 0
    allow_print: bool | None = None
    scope: str = "global"
