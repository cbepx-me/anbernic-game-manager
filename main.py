#!/usr/bin/env python3
# make by G.R.H

import os
import sys
import zipfile

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