"""`python -m fransys_kicad <file.kicad_sym> <symbol>` prints a part-file skeleton."""

import sys
from pathlib import Path

from .bootstrap import part_file_skeleton


def main(argv: list[str]) -> int:
    """Read the KiCad symbol library and write the skeleton to stdout."""
    library, symbol = argv
    sys.stdout.write(part_file_skeleton(Path(library).read_text(encoding="utf-8"), symbol))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
