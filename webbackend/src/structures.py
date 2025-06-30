from pydantic import BaseModel

class CodeRequest(BaseModel):
    pycode: str
