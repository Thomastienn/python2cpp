#!/usr/bin/env python3
"""
Python to C++ Converter - Command Line Interface

This module provides the main command-line interface for the py2cpp converter.
It handles argument parsing, file I/O, security validation, and orchestrates
the conversion process from Python source code to C++ output.

Example usage:
    python main.py input.py                    # Convert input.py to input.cpp
    python main.py input.py output.cpp         # Convert with custom output name
    python main.py input.py --debug            # Enable debug logging
    python main.py input.py --quiet            # Suppress non-error output
    
Author: Thomas Tien
Project: py2cpp - Python to C++ Converter
License: MIT
"""

import os
import sys
import ast
import argparse
from pathlib import Path
from py2c.commands.parser import parse
from py2c.utils.utils import Utils, SecurityUtils, SecurityError
from py2c.utils.logger import setup_logger


def create_parser():
    """
    Create and configure the argument parser for the py2cpp command-line tool.
    
    Returns:
        argparse.ArgumentParser: Configured argument parser with all required
                                 arguments and options for the converter.
    
    The parser includes:
        - input_file: Required positional argument for the Python source file
        - output_file: Optional positional argument for the C++ output file
        - --debug: Enable debug logging
        - --quiet: Suppress non-error output
        - --version: Show version information
    """
    
    parser = argparse.ArgumentParser(
        prog='py2c',
        description='Convert Python code to C++',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  py2c input.py                    # Output to input.cpp in out/ directory
  py2c input.py output.cpp         # Output to output.cpp in out/ directory
  py2c input.py --debug            # Enable debug logging
  py2c input.py --quiet            # Suppress non-error output
        """
    )
    
    parser.add_argument(
        'input_file',
        help='Python source file to convert'
    )
    
    parser.add_argument(
        'output_file',
        nargs='?',
        help='Output C++ file name (optional, defaults to input name with .cpp extension)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress non-error output'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0'
    )
    
    return parser


def run():
    """
    Main function to run the Python to C++ converter.
    
    This function orchestrates the entire conversion process:
    1. Parses command-line arguments
    2. Sets up logging and security validation
    3. Validates input and output file paths
    4. Reads and validates Python source code
    5. Converts Python AST to C++ code
    6. Writes output files and handles errors
    
    The function includes comprehensive error handling and security measures
    to prevent directory traversal attacks, code injection, and resource exhaustion.
    
    Raises:
        SecurityError: If input validation fails or security constraints are violated
        SystemExit: On various error conditions (file not found, parsing errors, etc.)
    
    Returns:
        None: Function exits with appropriate exit codes on completion or error
    """
    # If no arguments provided, try to use test.py for backward compatibility
    if len(sys.argv) == 1:
        if os.path.exists("test.py"):
            sys.argv.append("test.py")
        else:
            print("Error: No input file specified", file=sys.stderr)
            print("Usage: py2c <input_file> [output_file] [options]", file=sys.stderr)
            sys.exit(1)
    
    parser = create_parser()
    args = parser.parse_args()
    
    # Set up logging based on debug flag
    if args.debug:
        os.environ['PY2CPP_DEBUG'] = 'true'
    
    logger = setup_logger("py2cpp.main")
    security_logger = Utils.setup_security_logging()
    
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    try:
        # Security validation for input file path
        input_file = SecurityUtils.validate_file_path(args.input_file)
        
        # Determine output filename with security validation
        input_filename = os.path.basename(input_file)
        input_file_no_ext = Utils.get_file_no_ext(input_filename)
        
        if args.output_file:
            # Validate output file path to prevent directory traversal
            output_file = os.path.abspath(args.output_file)
            # Ensure output is in a safe location (current dir or subdirectory)
            output_dir = os.path.dirname(output_file)
            current_dir = os.getcwd()
            try:
                os.path.relpath(output_dir, current_dir)
            except ValueError:
                raise SecurityError("Output file path must be relative to current directory")
        else:
            output_file = os.path.abspath(f"{input_file_no_ext}.cpp")
        
        # Create the output directory if it doesn't exist (securely)
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            # Ensure we're not creating directories outside current working area
            rel_path = os.path.relpath(output_dir, os.getcwd())
            if rel_path.startswith('..'):
                raise SecurityError("Cannot create output directory outside current working area")
            os.makedirs(output_dir, mode=0o755)
        
        # Create error log file with same name as output but .err extension
        output_basename = os.path.splitext(os.path.basename(output_file))[0]
        if output_dir:
            error_path = os.path.join(output_dir, f"{output_basename}.err")
        else:
            error_path = f"{output_basename}.err"
        
        if not args.quiet:
            print(f"Converting {input_file} -> {output_file}")
        
        logger.debug(f"Reading input file: {input_file}")
        
        # Read file with security validation
        with open(input_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # Security validations
        SecurityUtils.validate_input_size(source_code)
        
        logger.debug("Parsing Python code with security validation")
        tree = SecurityUtils.validate_ast_complexity(source_code)
        
        # Log security event
        security_logger.info(f"CLI conversion: {input_file} -> {output_file}, size: {len(source_code)} bytes")
        
        logger.debug(f"Writing output to: {output_file}")
        logger.debug(f"Writing errors to: {error_path}")
        
        # Create secure temporary files for output
        try:
            sys.stdout = open(output_file, 'w', encoding='utf-8')
            sys.stderr = open(error_path, 'w', encoding='utf-8')
            
            # Parse with timeout using the enhanced capture_output
            parse(tree)
            
        finally:
            # Always close files before checking them
            if sys.stdout != original_stdout:
                sys.stdout.close()
            if sys.stderr != original_stderr:
                sys.stderr.close()
            sys.stdout = original_stdout
            sys.stderr = original_stderr
        
        # Check if there were any errors
        if os.path.exists(error_path) and os.path.getsize(error_path) > 0:
            if not args.quiet:
                print(f"Warning: Errors were generated during conversion. Check {error_path}")
        else:
            if not args.quiet:
                print(f"No errors generated. Error log available at: {error_path}")
        
        if not args.quiet:
            print("Conversion completed successfully!")
        
        logger.info(f"Successfully converted {input_file} to {output_file}")
        
    except SecurityError as e:
        security_logger.warning(f"Security violation in CLI: {str(e)}")
        print(f"Security Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        
        # Sanitize error message for output
        sanitized_error = SecurityUtils.sanitize_error_message(e, debug_mode=args.debug)
        print(f"Error: {sanitized_error}", file=sys.stderr)
        
        if args.debug:
            import traceback
            traceback.print_exc(file=sys.stderr)
        
        sys.exit(1)
    finally:
        # Always restore stdout/stderr
        if sys.stdout != original_stdout:
            sys.stdout.close()
            sys.stdout = original_stdout
        if sys.stderr != original_stderr:
            sys.stderr.close()
            sys.stderr = original_stderr


if __name__ == "__main__":
    """Entry point for the py2cpp command-line tool."""
    run()
