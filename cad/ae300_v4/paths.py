"""Resolve both repository and unpacked-delivery layouts."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
OUT = HERE.parent if HERE.parent.name == 'AE300_R4' else HERE.parents[1] / 'output' / 'ae300_r4'
