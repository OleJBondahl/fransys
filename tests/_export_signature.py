"""The export's signature (R462): the `internal/` root is absent from the tree.

The private repo has it, so a lost private input still fails there; only the export lacks it.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_REASON = "private input; runs in the private repo (R462)"


def is_export(root: Path = ROOT) -> bool:
    """True when `root` is a public export: it has no `internal/` folder."""
    return not (root / "internal").is_dir()
