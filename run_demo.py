#!/usr/bin/env python3
"""
Convenience script to run the demo from the project root.

This ensures proper Python path setup regardless of how it's invoked.
"""

import sys
from pathlib import Path

# Ensure we're in the project root
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Change to project root directory
import os
os.chdir(project_root)

# Now run the demo
from demo.main import main

if __name__ == "__main__":
    main()

