"""`python -m fransys`: the developer verbs.

`parts-module` writes the typed parts module, `help KEY` looks a key up, `migrate-parts DIR` moves a schema 1 part library to schema 2.
"""

import sys
from pathlib import Path

from fransys._help import help_text
from fransys.migrate_parts import migrate_parts
from fransys.parts_module import parts_module

MIN_ARGS = 3
HELP_ARGS = 2
USAGE = "usage: python -m fransys parts-module LIBRARY [LIBRARY ...] OUT | help KEY | migrate-parts DIR"


def main(argv: list[str]) -> int:
    if argv[:1] == ["help"] and len(argv) == HELP_ARGS:
        text, code = help_text(argv[1])
        sys.stdout.write(text + "\n")
        return code
    if argv[:1] == ["migrate-parts"] and len(argv) == HELP_ARGS:
        return migrate_parts(Path(argv[1]))
    if len(argv) < MIN_ARGS or argv[0] != "parts-module":
        sys.stderr.write(USAGE + "\n")
        return 2
    *libraries, out = argv[1:]
    Path(out).write_text(parts_module(*libraries), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
