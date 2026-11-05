"""`python -m fransys migrate-parts DIR`: the files of every part library under DIR, schema 1 to schema 2, in place."""

import sys
lazy from pathlib import Path

from fransys_parts import PartLibraryError, migrate_part_text


def _rewrite(path: Path) -> bool:
    """Rewrite one file when it is schema 1; False and a line on stderr naming the file when it cannot be read or converted."""
    try:
        old = path.read_text(encoding="utf-8")
        new = migrate_part_text(old)
    except (OSError, UnicodeDecodeError, PartLibraryError) as error:
        sys.stderr.write(f"{path}: {error}. Fix the file as the message says, then run migrate-parts again.\n")
        return False
    if new != old:
        path.write_text(new, encoding="utf-8")
        sys.stdout.write(f"rewrote {path}\n")
    return True


def migrate_parts(directory: Path) -> int:
    """Convert every library under `directory`, its part files first and `library.toml` only when none failed; 1 on a failure."""
    libraries = list(directory.rglob("library.toml"))
    if not libraries:
        sys.stderr.write(
            f"{directory}: no library.toml under this folder, so no part library to convert. "
            "Give the library's folder (the one holding library.toml and parts/) or a folder above it, never its parts/ folder.\n"
        )
        return 1
    ok = True
    for library in libraries:
        converted = [_rewrite(path) for path in library.with_name("parts").glob("*.toml")]  # every file, no short-circuit
        ok = all(converted) and _rewrite(library) and ok
    return 0 if ok else 1
