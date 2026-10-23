"""The P7.3 PNG pair set: each case has a today and a core picture per role, or a named reason."""

from pathlib import Path

CASES = ("w04", "own")
ROLES = ("cover", "schematic", "terminal-list", "bom")


def missing_pairs(directory: str | Path, reasons: dict[str, str] | None = None) -> list[str]:
    """Each `<case>-<role>-<side>.png` absent from `directory` with no reason named for it."""
    directory = Path(directory)
    reasons = reasons or {}
    absent = []
    for case in CASES:
        for role in ROLES:
            for side in ("before", "after"):
                name = f"{case}-{role}-{side}.png"
                if not (directory / name).is_file() and name not in reasons:
                    absent.append(name)
    return absent
