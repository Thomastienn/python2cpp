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


class SecurityError(Exception):
    """Custom exception for security-related errors"""
    pass


class SecurityUtils:
    """Security utility functions for input validation and sanitization"""
    
    @staticmethod
    def validate_input_size(content: str, max_size: Optional[int] = None) -> None:
        """Validate input size to prevent resource exhaustion"""
        max_size = max_size or SECURITY_CONFIG['MAX_INPUT_SIZE']
        if len(content.encode('utf-8')) > max_size:
            raise SecurityError(f"Input size exceeds maximum allowed size of {max_size} bytes")
    
    @staticmethod
    def validate_ast_complexity(code: str, max_nodes: Optional[int] = None) -> ast.AST:
        """Parse and validate AST complexity to prevent resource exhaustion"""
        max_nodes = max_nodes or SECURITY_CONFIG['MAX_AST_NODES']
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise SecurityError(f"Invalid Python syntax: {str(e)}")
        
        # Count AST nodes
        node_count = sum(1 for _ in ast.walk(tree))
        if node_count > max_nodes:
            raise SecurityError(f"Code complexity exceeds limit ({node_count} > {max_nodes} nodes)")
        
        return tree
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal attacks"""
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
        """Validate and resolve file path to prevent directory traversal"""
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
        """Create a secure temporary file"""
        try:
            fd, path = tempfile.mkstemp(suffix=suffix, prefix="py2cpp_")
            return fd, path
        except OSError as e:
            raise SecurityError(f"Failed to create secure temporary file: {str(e)}")
    
    @staticmethod
    def sanitize_error_message(error: Exception, debug_mode: bool = False) -> str:
        """Sanitize error messages to prevent information disclosure"""
        if debug_mode:
            return str(error)
        
        # Generic error messages for security
        if isinstance(error, SyntaxError):
            return "Invalid Python syntax in input code"
        elif isinstance(error, SecurityError):
            return str(error)  # Security errors are safe to expose
        elif isinstance(error, MemoryError):
            return "Input code is too complex or large"
        elif isinstance(error, TimeoutError):
            return "Code processing timed out"
        else:
            return "An error occurred while processing your code"


class TimeoutContext:
    """Context manager for implementing timeouts"""
    
    def __init__(self, timeout_seconds: int):
        self.timeout_seconds = timeout_seconds
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def check_timeout(self):
        """Check if timeout has been exceeded"""
        if self.start_time and (time.time() - self.start_time) > self.timeout_seconds:
            raise TimeoutError(f"Operation timed out after {self.timeout_seconds} seconds")


# Original Utils class with security enhancements
class Utils:
    # List of names of template used. Must be the name of the enum
    template_uses: set[str] = set()
    
    @staticmethod
    def get_file_no_ext(filename):
        if "." in filename:
            return filename.split(".")[0]
        else:
            return filename
    
    @staticmethod
    def capture_output(func, *args, **kwargs):
        """Capture function output with security enhancements"""
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
            raise SecurityError(f"Processing failed: {type(e).__name__}")
    
    @staticmethod
    def setup_security_logging() -> logging.Logger:
        """Setup security event logging"""
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




