#!/usr/bin/env python3
# make by G.R.H

import os
import sys
import zipfile
from pathlib import Path

try:
    board_info = Path("/mnt/vendor/oem/board.ini").read_text().splitlines()[0]
    board_mapping = {
        'RGcubexx': 1,
        'RG34xx': 2,
        'RG34xxSP': 2,
        'RGSP': 2,
        'RG28xx': 3,
        'RG35xx+_P': 4,
        'RG35xxH': 5,
        'RG35xxSP': 6,
        'RG40xxH': 7,
        'RG40xxV': 8,
        'RG35xxPRO': 9,
        "RGds": 10,
        "RGdsplus": 11
    }
    hw_info = board_mapping.get(board_info, 5)
except:
    hw_info = 5

def ensure_requests():
    try:
        program = os.path.dirname(os.path.abspath(__file__))
        depspath = os.path.join(program, "deps")
        if not os.path.exists(depspath):
            module_file = os.path.join(program, "module.zip")
            with zipfile.ZipFile(module_file, 'r') as zip_ref:
                zip_ref.extractall(program)
            print("Successfully installed sdl2 and PIL and flask")
        return True
    except Exception as e:
        print(f"Failed to install: {e}")
        return False


def main():
    if ensure_requests():
        base_path = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, os.path.join(base_path, "deps"))
        import app
        app.main()

if __name__ == "__main__":
    main()