"""
ULog placeholder classifier.

Behavior: copy every file from /in to /out unchanged, and print a tiny log.
This proves the local volumes + container wiring work for newcomers.
"""

import os
from pathlib import Path
import shutil
import sys

IN_DIR = Path(os.getenv("IN_DIR", "/in"))
OUT_DIR = Path(os.getenv("OUT_DIR", "/out"))

def main() -> int:
    IN_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    files = [p for p in IN_DIR.iterdir() if p.is_file()]
    if not files:
        print("classifier: no files found in /in. Tip: run `make generate`.", flush=True)
        return 0

    for p in files:
        dest = OUT_DIR / p.name
        shutil.copy2(p, dest)
        print(f"classifier: copied {p.name} -> {dest}", flush=True)

    # Drop a marker so users can see it worked
    (OUT_DIR / "_DONE").write_text("ok\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
