"""
Data structures for the Python to C++ converter API.

This module defines the Pydantic models used for request validation
and data handling in the API services. It ensures that inputs meet
specific criteria before processing and conversion.

Security features include input size restrictions and validation
against dangerous code patterns such as the use of blacklisted imports.

Author: Thomas Tien
Project: py2cpp - Python to C++ Converter
License: MIT
"""

from pydantic import BaseModel, Field, field_validator
from py2c.utils.constants import SECURITY_CONFIG


class PyCodeRequest(BaseModel):
    """
    Pydantic model representing a code conversion request.

    Attributes:
        pycode (str): The Python code to be converted to C++.

    Validation:
        - Ensures the code is within length constraints
        - Performs basic validation against dangerous import usage
    """

    pycode: str = Field(
        ..., 
        min_length=1,
        max_length=SECURITY_CONFIG['MAX_INPUT_SIZE'],
        description="Python code to convert to C++"
    )
    
    @field_validator('pycode')
    @classmethod
    def validate_pycode(cls, v: str) -> str:
        """
        Validate Python code input for size and unauthorized imports.

        Args:
            v (str): The input Python code to be validated.

        Returns:
            str: The validated Python code, unchanged if valid.

        Raises:
            ValueError: If the code is empty or contains dangerous imports.
        """
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

class CppCodeRequest(BaseModel):
    """
    Pydantic model representing a code fix request.

    Attributes:
        cppcode (str): The C++ code to be validated and fixed.
    Validation:
        - Ensures the code is not exceed length constraints
    """

    cppcode: str = Field(
        ..., 
        min_length=1,
        max_length=SECURITY_CONFIG['MAX_INPUT_SIZE'],
        description="C++ code to validate and fix"
    )
