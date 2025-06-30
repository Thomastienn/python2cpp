import os
import sys
import ast
import argparse
from pathlib import Path
from py2c.commands.parser import parse
from py2c.utils.utils import Utils
from py2c.utils.logger import setup_logger

def create_parser():
    """Create and configure the argument parser."""
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
    """Main function to run the converter."""
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
    
    # Validate input file
    input_file = args.input_file
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist", file=sys.stderr)
        sys.exit(1)
        
    if not os.path.isfile(input_file):
        print(f"Error: '{input_file}' is not a file", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Determine output filename
        input_filename = os.path.basename(input_file)
        input_file_no_ext = Utils.get_file_no_ext(input_filename)
        
        if args.output_file:
            output_file = args.output_file
        else:
            output_file = f"{input_file_no_ext}.cpp"
        
        # Create the output directory if it doesn't exist
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Create error log file with same name as output but .err extension
        output_basename = os.path.splitext(os.path.basename(output_file))[0]
        if output_dir:
            error_path = os.path.join(output_dir, f"{output_basename}.err")
        else:
            error_path = f"{output_basename}.err"
        
        if not args.quiet:
            print(f"Converting {input_file} -> {output_file}")
        
        logger.debug(f"Reading input file: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        logger.debug("Parsing Python code")
        tree = ast.parse(source_code)
        
        # Redirect stdout and stderr for the conversion process
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        logger.debug(f"Writing output to: {output_file}")
        logger.debug(f"Writing errors to: {error_path}")
        
        sys.stdout = open(output_file, 'w', encoding='utf-8')
        sys.stderr = open(error_path, 'w', encoding='utf-8')
        
        try:
            parse(tree)
        finally:
            # Always restore stdout/stderr and close files
            sys.stdout.close()
            sys.stderr.close()
            sys.stdout = original_stdout
            sys.stderr = original_stderr
        
        # Check if there were any errors
        if os.path.getsize(error_path) > 0:
            if not args.quiet:
                print(f"Warning: Errors were generated during conversion. Check {error_path}")
        else:
            if not args.quiet:
                print(f"No errors generated. Error log available at: {error_path}")
        
        if not args.quiet:
            print("Conversion completed successfully!")
        
        logger.info(f"Successfully converted {input_file} to {output_file}")
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        print(f"Error: Conversion failed - {e}", file=sys.stderr)
        
        if args.debug:
            import traceback
            traceback.print_exc()
        
        sys.exit(1)

if __name__ == "__main__":
    run()
