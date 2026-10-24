import os
import sys

DV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if DV not in sys.path:
    sys.path.insert(0, DV)