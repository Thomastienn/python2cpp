#!/usr/bin/env python3
"""
CLI entry point for py2cpp.
This module serves as a wrapper to import and call the main function.
"""

import os
import sys
from pathlib import Path

def main():
    """Entry point for the py2c command."""
    # Add the project root directory to sys.path so we can import main.py
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    try:
        # Import and call the run function from main.py
        from main import run
        run()
    except ImportError as e:
        print(f"Error: Could not import main module: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
