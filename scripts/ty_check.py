"""`just check`'s ty step: `ty check` with `--project` set to the cwd in its real on-disk case.

ty keys modules by the path's spelling; a cwd typed in another case loads each package twice
(LEAN LC5). `Path.resolve` returns the true case on Windows. This stays a Python helper, not a
`$(...)` in the justfile, so no recipe needs `sh` on a Windows PATH.

Not a package module: `uv run python scripts/ty_check.py`.
"""

import subprocess
import sys
from pathlib import Path


def command(root: Path) -> list[str]:
    """The `ty check` argv: one `--extra-search-path` per line of `internal/search-paths.txt`, when the full repo has it."""
    listed = root / "internal" / "search-paths.txt"
    extra = [a for line in listed.read_text("utf-8").split() for a in ("--extra-search-path", line)] if listed.is_file() else []
    return ["uv", "run", "ty", "check", "--project", str(root), *extra]


def main() -> int:
    """Run `ty check --project <resolved cwd>`; return ty's own exit code."""
    return subprocess.run(command(Path.cwd().resolve()), check=False).returncode  # noqa: S603


if __name__ == "__main__":
    sys.exit(main())
