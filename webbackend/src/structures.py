from pydantic import BaseModel, Field, field_validator
from py2c.utils.constants import SECURITY_CONFIG


class CodeRequest(BaseModel):
    pycode: str = Field(
        ..., 
        min_length=1,
        max_length=SECURITY_CONFIG['MAX_INPUT_SIZE'],
        description="Python code to convert to C++"
    )
    
    @field_validator('pycode')
    @classmethod
    def validate_pycode(cls, v: str) -> str:
        """Validate Python code input"""
        # Basic validation
        if not v.strip():
            raise ValueError("Python code cannot be empty")
        
        # Check for potentially dangerous imports (basic heuristic)
        dangerous_imports = ['os', 'sys', 'subprocess', 'eval', 'exec', '__import__']
        lines = v.lower().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                for dangerous in dangerous_imports:
                    if dangerous in line:
                        raise ValueError(f"Potentially unsafe import detected: {dangerous}")
        
        return v
