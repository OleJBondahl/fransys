"""`python -m fransys parts-module LIBRARY [LIBRARY ...] OUT` writes the typed parts module."""

import sys
from pathlib import Path

from fransys.parts_module import parts_module

MIN_ARGS = 3
USAGE = "usage: python -m fransys parts-module LIBRARY [LIBRARY ...] OUT"


def main(argv: list[str]) -> int:
    if len(argv) < MIN_ARGS or argv[0] != "parts-module":
        sys.stderr.write(USAGE + "\n")
        return 2
    *libraries, out = argv[1:]
    Path(out).write_text(parts_module(*libraries), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
