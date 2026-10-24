#!/usr/bin/env python3
"""Entrypoint"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rrdv.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
