"""
Custom Exception Classes for Python to C++ Conversion

This module defines custom exception classes used throughout the py2cpp converter
to provide specific error handling and reporting for different types of errors
that can occur during the conversion process.

Exception Hierarchy:
- ErrorUsage: Incorrect program usage
- UserError: Errors in user's Python code
- ParserError: Errors in AST processing
- VisitorError: Errors in code generation
- LinterError: Errors in type checking and validation

Author: Thomas Tien
Project: py2cpp - Python to C++ Converter
License: MIT
"""


class ErrorUsage(Exception):
    """
    Exception raised when the user uses the program incorrectly.
    
    This exception is raised when the user provides invalid arguments,
    incorrect usage patterns, or violates the expected program interface.
    """
    pass


class UserError(Exception):
    """
    Exception raised when the user's Python code has an error.
    
    This exception is raised when the input Python code contains syntax errors,
    semantic errors, or uses unsupported Python features.
    """
    pass


class ParserError(Exception):
    """
    Base exception class for the main AST processor.
    
    This exception is raised when the parser encounters an error during
    AST traversal, node processing, or code generation.
    """
    pass


class VisitorError(Exception):
    """
    Base exception class for the AST visitor.
    
    This exception is raised when the visitor encounters an error during
    expression evaluation, type inference, or C++ code generation.
    """
    pass


class LinterError(Exception):
    """
    Base exception class for the linter.
    
    This exception is raised when the linter encounters an error during
    type checking, variable resolution, or scope management.
    """
    pass
