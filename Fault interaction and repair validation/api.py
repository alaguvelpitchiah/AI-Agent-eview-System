#!/usr/bin/env python3
import runpy
from pathlib import Path

DIR = Path(__file__).resolve().parent
TARGET = DIR / "server.py"

if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
