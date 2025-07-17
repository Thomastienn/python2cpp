import sys, io
import ast
import os
import re
import time
import tempfile
import logging
from pathlib import Path
from typing import Optional, Tuple, Any

from py2c.utils.constants import SECURITY_CONFIG
import py2c.core.errors as ParsingErrors


class SecurityError(Exception):
    """Custom exception for security-related errors"""
    pass


class SecurityUtils:
    """
    Security utility functions for input validation and sanitization.
    
    This class provides static methods to validate and sanitize inputs
    to prevent security vulnerabilities such as:
    - Resource exhaustion attacks
    - Directory traversal attacks
    - Code injection attacks
    - Information disclosure
    
    All methods are static and can be called without instantiating the class.
    """
    
    @staticmethod
    def validate_input_size(content: str, max_size: Optional[int] = None) -> None:
        """
        Validate input size to prevent resource exhaustion attacks.
        
        Args:
            content (str): The input content to validate
            max_size (Optional[int]): Maximum allowed size in bytes.
                                    If None, uses SECURITY_CONFIG['MAX_INPUT_SIZE']
        
        Raises:
            SecurityError: If the input size exceeds the maximum allowed size
        """
        max_size = max_size or SECURITY_CONFIG['MAX_INPUT_SIZE']
        if len(content.encode('utf-8')) > max_size:
            raise SecurityError(f"Input size exceeds maximum allowed size of {max_size} bytes")
    
    @staticmethod
    def validate_ast_complexity(code: str, max_nodes: Optional[int] = None) -> ast.AST:
        """
        Parse and validate AST complexity to prevent resource exhaustion.
        
        Args:
            code (str): The Python code to parse and validate
            max_nodes (Optional[int]): Maximum number of AST nodes allowed.
                                     If None, uses SECURITY_CONFIG['MAX_AST_NODES']
        
        Returns:
            ast.AST: The parsed AST if validation passes
        
        Raises:
            SecurityError: If AST complexity exceeds the limit
            UserError: If the code contains syntax errors
        """
        max_nodes = max_nodes or SECURITY_CONFIG['MAX_AST_NODES']
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ParsingErrors.UserError(f"Invalid Python syntax: {str(e)}")
        
        # Count AST nodes
        node_count = sum(1 for _ in ast.walk(tree))
        if node_count > max_nodes:
            raise SecurityError(f"Code complexity exceeds limit ({node_count} > {max_nodes} nodes)")
        
        return tree
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal attacks.
        
        Args:
            filename (str): The filename to sanitize
        
        Returns:
            str: The sanitized filename
        
        Raises:
            SecurityError: If the filename contains invalid characters or extensions
        """
        # Remove any path components
        filename = os.path.basename(filename)
        
        # Check against allowed pattern
        if not re.match(SECURITY_CONFIG['SECURE_FILENAME_PATTERN'], filename):
            raise SecurityError("Filename contains invalid characters")
        
        # Check file extension
        _, ext = os.path.splitext(filename)
        if ext.lower() not in SECURITY_CONFIG['ALLOWED_EXTENSIONS']:
            raise SecurityError(f"File extension '{ext}' not allowed")
        
        return filename
    
    @staticmethod
    def validate_file_path(file_path: str) -> str:
        """
        Validate and resolve file path to prevent directory traversal.
        
        Args:
            file_path (str): The file path to validate
        
        Returns:
            str: The resolved absolute path if validation passes
        
        Raises:
            SecurityError: If the file path is invalid, doesn't exist, or exceeds size limits
        """
        try:
            # Convert to Path object and resolve
            path = Path(file_path).resolve()
            
            # Ensure the path exists and is a file
            if not path.exists():
                raise SecurityError(f"File does not exist: {file_path}")
            
            if not path.is_file():
                raise SecurityError(f"Path is not a file: {file_path}")
            
            # Check file size
            file_size = path.stat().st_size
            if file_size > SECURITY_CONFIG['MAX_FILE_SIZE']:
                raise SecurityError(f"File size exceeds limit ({file_size} > {SECURITY_CONFIG['MAX_FILE_SIZE']} bytes)")
            
            return str(path)
        except (OSError, ValueError) as e:
            raise SecurityError(f"Invalid file path: {str(e)}")
    
    @staticmethod
    def create_secure_temp_file(suffix: str = ".tmp") -> Tuple[int, str]:
        """
        Create a secure temporary file.
        
        Args:
            suffix (str): File extension suffix for the temporary file
        
        Returns:
            Tuple[int, str]: File descriptor and path of the created temporary file
        
        Raises:
            SecurityError: If temporary file creation fails
        """
        try:
            fd, path = tempfile.mkstemp(suffix=suffix, prefix="py2cpp_")
            return fd, path
        except OSError as e:
            raise SecurityError(f"Failed to create secure temporary file: {str(e)}")
    
    @staticmethod
    def sanitize_error_message(error: Exception, debug_mode: bool = False) -> str:
        """
        Sanitize error messages to prevent information disclosure.
        
        Args:
            error (Exception): The exception to sanitize
            debug_mode (bool): Whether to include full error details
        
        Returns:
            str: Sanitized error message safe for user display
        """
        if debug_mode:
            return str(error)

        if isinstance(error, NotImplementedError):
            return "This feature is not implemented yet\n" + str(error)

        if isinstance(error, ParsingErrors.ErrorUsage):
            return "You are using a feature that is not supported\n" + str(error)

        if isinstance(error, ParsingErrors.UserError):
            return "There is an error in your code\n" + str(error)

        if isinstance(error, ParsingErrors.ParserError):
            return "My main processing (ExprParser) has an error\n" + str(error)

        if isinstance(error, ParsingErrors.VisitorError):
            return "My repr visitor (ReprVisitor) has an error\n" + str(error)

        if isinstance(error, ParsingErrors.LinterError):
            return "My linter (Linter) has an error\n" + str(error)
        
        if isinstance(error, SecurityError):
            return str(error)  # Security errors are safe to expose

        if isinstance(error, MemoryError):
            return "Input code is too complex or large"

        if isinstance(error, TimeoutError):
            return "Code processing timed out"

        return "An error occurred while processing your code"


class TimeoutContext:
    """
    Context manager for implementing timeouts in code execution.
    
    This class provides a simple way to add timeout functionality to any
    operation by tracking elapsed time and raising TimeoutError when exceeded.
    
    Attributes:
        timeout_seconds (int): Maximum allowed execution time in seconds
        start_time (float): Timestamp when the context was entered
    
    Example:
        with TimeoutContext(30) as ctx:
            # Long running operation
            result = process_data()
            ctx.check_timeout()  # Raises TimeoutError if > 30 seconds
    """
    
    def __init__(self, timeout_seconds: int):
        """
        Initialize the timeout context.
        
        Args:
            timeout_seconds (int): Maximum allowed execution time in seconds
        """
        self.timeout_seconds = timeout_seconds
        self.start_time = None
    
    def __enter__(self):
        """
        Enter the timeout context and start timing.
        
        Returns:
            TimeoutContext: Self reference for method chaining
        """
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the timeout context. No cleanup needed.
        
        Args:
            exc_type: Exception type (if any)
            exc_val: Exception value (if any)
            exc_tb: Exception traceback (if any)
        """
        pass
    
    def check_timeout(self):
        """
        Check if the timeout has been exceeded.
        
        Raises:
            TimeoutError: If the elapsed time exceeds the timeout threshold
        """
        if self.start_time and (time.time() - self.start_time) > self.timeout_seconds:
            raise TimeoutError(f"Operation timed out after {self.timeout_seconds} seconds")


class Utils:
    """
    General utility functions for the py2cpp converter.
    
    This class provides various utility functions used throughout the converter,
    including output capture, file handling, and template management.
    
    Class Attributes:
        template_uses (set[str]): Set of template names that have been used
                                 during conversion. Used to track which C++
                                 templates need to be included in the output.
    """
    
    # List of names of template used. Must be the name of the enum
    template_uses: set[str] = set()

    def generate_unique_filename(base: str) -> str:
        """
        Generate a unique filename by appending a counter to the base name.
        
        Args:
            base (str): The base filename to use.
        
        Returns:
            str: A unique filename with a counter appended.
        """
        timed_base = f"{base}_{int(time.time())}"
        if os.path.exists(timed_base):
            counter = 1
            while os.path.exists(f"{timed_base}_{counter}"):
                counter += 1
            return f"{timed_base}_{counter}"
        return timed_base
    
    @staticmethod
    def get_file_no_ext(filename):
        """
        Extract the filename without extension.
        
        Args:
            filename (str): The filename to process
        
        Returns:
            str: The filename without its extension
        
        Example:
            get_file_no_ext("test.py") -> "test"
            get_file_no_ext("noextension") -> "noextension"
        """
        if "." in filename:
            return filename.split(".")[0]
        else:
            return filename
    
    @staticmethod
    def capture_output(func, *args, **kwargs):
        """
        Capture function output with security enhancements and timeout protection.
        
        This function redirects stdout to capture the output of a function call,
        with added security measures including timeout protection.
        
        Args:
            func: The function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function. Special kwargs:
                     - timeout: Maximum execution time in seconds
                     - include_return: If True, return (output, return_value)
        
        Returns:
            str: The captured stdout output, or
            tuple: (output, return_value) if include_return=True
        
        Raises:
            SecurityError: If security constraints are violated
            TimeoutError: If execution exceeds the timeout
            Exception: Re-raises any exceptions from the wrapped function
        """
        timeout = kwargs.pop('timeout', SECURITY_CONFIG['CONVERSION_TIMEOUT'])
        
        original = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            with TimeoutContext(timeout) as timeout_ctx:
                # Check timeout periodically during execution
                ret = func(*args)
                timeout_ctx.check_timeout()
            
            output = sys.stdout.getvalue()
            sys.stdout = original
            
            if "include_return" in kwargs and kwargs["include_return"]:
                return output, ret
            return output
            
        except Exception as e:
            sys.stdout = original
            # Re-raise security errors and timeouts
            if isinstance(e, (SecurityError, TimeoutError)):
                raise
            # For other errors, wrap them for consistent handling
            raise type(e)(f"Processing failed: {e}")
    
    @staticmethod
    def setup_security_logging() -> logging.Logger:
        """
        Setup security event logging for the application.
        
        Creates a dedicated logger for security events with file-based output.
        This logger is used to track security-related events such as:
        - Input validation failures
        - Rate limit violations
        - IP bans and abuse attempts
        - Conversion requests and their metadata
        
        Returns:
            logging.Logger: Configured security logger instance
        
        The logger outputs to 'security.log' file with timestamp formatting.
        """
        logger = logging.getLogger("py2cpp.security")
        
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            
            # Create file handler for security events
            handler = logging.FileHandler("security.log", mode='a')
            handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - SECURITY - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
