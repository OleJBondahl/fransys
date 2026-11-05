"""Every warning in the `findings-*.md` pages is actionable (WARNINGS-ACTIONABLE, decision 0180).

A1: no WARNING row says "nothing to fix" or "accept". A2: every row names who acts. A row's severity
is its `CodeInfo.severity`, the one home (decision 0410), so the table is generated, not scanned.
"""

from __future__ import annotations

import re
from importlib.resources import files

FINDINGS_PAGES = (
    "findings-validators",
    "findings-release",
    "findings-render",
    "findings-pdf",
    "findings-kicad",
    "findings-parts",
)
_WHO = frozenset({"consumer", "part author", "Fransys", "note"})
_BANNED = re.compile(r"nothing to fix|accept", re.IGNORECASE)


def table_rows(markdown: str) -> list[list[str]]:
    """One findings page's data rows: code, severity, stage, who acts, meaning, fix."""
    lines = [x.strip() for x in markdown.splitlines() if x.strip().startswith("|")]
    return [[c.strip() for c in line.strip("|").split("|")] for line in lines[2:]]


def _guide_rows() -> list[list[str]]:
    return [row for page in FINDINGS_PAGES for row in table_rows(files("fransys").joinpath("guide", f"{page}.md").read_text(encoding="utf-8"))]


def a1_violations(rows: list[list[str]]) -> list[str]:
    """Codes whose WARNING remedy says to accept it or that nothing is to be fixed."""
    return [r[0] for r in rows if "WARNING" in r[1] and _BANNED.search(r[5])]


def a2_violations(rows: list[list[str]]) -> list[str]:
    """Codes whose "Who acts" cell is not one of the three classes."""
    return [r[0] for r in rows if r[3] not in _WHO]


def test_no_warning_remedy_says_nothing_to_fix_or_accept():
    assert a1_violations(_guide_rows()) == []


def test_every_row_says_who_acts():
    assert a2_violations(_guide_rows()) == []


_OLD_LABEL_UNPLACED = [
    "LABEL_UNPLACED",
    "WARNING",
    "render",
    "consumer",
    "m",
    "Usually nothing to fix; if wrong, rearrange the crowded symbols or wires.",
]


def test_a1_fails_on_the_old_label_unplaced_remedy():
    """Probe: the old remedy put back is a violation."""
    assert a1_violations([_OLD_LABEL_UNPLACED]) == ["LABEL_UNPLACED"]


def test_a2_fails_on_a_blank_who_acts():
    """Probe: a blank cell is a violation."""
    assert a2_violations([["X_CODE", "WARNING", "render", "", "m", "f"]]) == ["X_CODE"]
