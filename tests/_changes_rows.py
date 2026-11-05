"""The stored change list of a release, for the changes-rename field cases."""

import csv
import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def changes_rows(release: Path) -> list[dict[str, str]]:
    """The stored change list of a release, one dict per CSV row."""
    text = (release / "data" / "changes.csv").read_text(encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def rows_of(rows: list[dict[str, str]], section: str, change: str) -> list[dict[str, str]]:
    return [r for r in rows if r["section"] == section and r["change"] == change]
