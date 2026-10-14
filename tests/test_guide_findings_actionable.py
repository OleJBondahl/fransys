"""Every warning in the `findings-*.md` pages is actionable (WARNINGS-ACTIONABLE, decision 0180).

A1: no WARNING row says "nothing to fix" or "accept". A2: every row names who acts. A3: the
severity of every row equals the severity the code gives its finding. A3 reads the sources with
`ast`: a call that holds a code (a string, or a constant naming one) and a `Severity.X` pairs them.
"""

from __future__ import annotations

import ast
import re
from importlib.resources import files
from pathlib import Path

import pytest

PACKAGES = Path(__file__).resolve().parent.parent / "packages"
FINDINGS_PAGES = (
    "findings-validators",
    "findings-render",
    "findings-pdf",
    "findings-kicad",
    "findings-parts",
)
_WHO = frozenset({"consumer", "part author", "Fransys", "note"})
_BANNED = re.compile(r"nothing to fix|accept", re.IGNORECASE)
_CODE_SHAPE = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)+$")
_MIN_COVERED = 100  # codes whose severity the scan sees; far below today's count, above vacuity


def table_rows(markdown: str) -> list[list[str]]:
    """One findings page's data rows: code, severity, stage, who acts, meaning, fix."""
    lines = [x.strip() for x in markdown.splitlines() if x.strip().startswith("|")]
    return [[c.strip() for c in line.strip("|").split("|")] for line in lines[2:]]


def _guide_rows() -> list[list[str]]:
    return [
        row
        for page in FINDINGS_PAGES
        for row in table_rows(
            files("fransys").joinpath("guide", f"{page}.md").read_text(encoding="utf-8")
        )
    ]


def a1_violations(rows: list[list[str]]) -> list[str]:
    """Codes whose WARNING remedy says to accept it or that nothing is to be fixed."""
    return [r[0] for r in rows if "WARNING" in r[1] and _BANNED.search(r[5])]


def a2_violations(rows: list[list[str]]) -> list[str]:
    """Codes whose "Who acts" cell is not one of the three classes."""
    return [r[0] for r in rows if r[3] not in _WHO]


def _sources() -> list[ast.Module]:
    return [
        ast.parse(p.read_text(encoding="utf-8")) for p in sorted(PACKAGES.glob("*/src/**/*.py"))
    ]


def _constants(trees: list[ast.Module]) -> dict[str, str]:
    """Module-level `NAME = "literal"` assignments, by name (code constants are unique)."""
    found: dict[str, str] = {}
    for tree in trees:
        for node in tree.body:
            target, value = None, None
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target, value = node.targets[0], node.value
            elif isinstance(node, ast.AnnAssign):
                target, value = node.target, node.value
            if (
                isinstance(target, ast.Name)
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                found[target.id] = value.value
    return found


def _code_of(arg: ast.expr, constants: dict[str, str]) -> str | None:
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        value = arg.value
    elif isinstance(arg, ast.Name):
        value = constants.get(arg.id, "")
    else:
        return None
    return value if _CODE_SHAPE.match(value) else None


def _severity_of(arg: ast.expr) -> str | None:
    if isinstance(arg, ast.Attribute) and isinstance(arg.value, ast.Name):
        return arg.attr if arg.value.id == "Severity" else None
    return None


def emitted_severities(known: frozenset[str]) -> dict[str, set[str]]:
    """Code to the severities `Severity.X` written beside it in one call."""
    trees = _sources()
    constants = _constants(trees)
    found: dict[str, set[str]] = {}
    for tree in trees:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            args = [*node.args, *(kw.value for kw in node.keywords)]
            sevs = {s for a in args if (s := _severity_of(a))}
            codes = {c for a in args if (c := _code_of(a, constants)) in known}
            if len(codes) == 1 and len(sevs) == 1:
                found.setdefault(codes.pop(), set()).update(sevs)
    return found


def a3_violations(rows: list[list[str]], emitted: dict[str, set[str]]) -> list[str]:
    """Codes whose table severity differs from the severities the code gives its findings."""
    bad = []
    for code, severity, *_ in rows:
        sevs = emitted.get(code)
        if sevs and set(severity.split(" or ")) != sevs:
            bad.append(code)
    return bad


def test_no_warning_remedy_says_nothing_to_fix_or_accept():
    assert a1_violations(_guide_rows()) == []


def test_every_row_says_who_acts():
    assert a2_violations(_guide_rows()) == []


def test_every_severity_matches_the_code():
    rows = _guide_rows()
    emitted = emitted_severities(frozenset(r[0] for r in rows))
    assert len(emitted) >= _MIN_COVERED
    assert a3_violations(rows, emitted) == []


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


def test_a3_fails_on_a_demoted_code_still_warning_in_code():
    """Probe: the table says INFO, the code says WARNING."""
    assert a3_violations(
        [["X_CODE", "INFO", "render", "note", "m", "f"]], {"X_CODE": {"WARNING"}}
    ) == ["X_CODE"]


@pytest.mark.parametrize(
    "code", ["NET_SINGLE_PIN", "DIAGRAM_CABLE_FANOUT", "DESIGNATION_NEW_IN_REVISION"]
)
def test_the_demoted_codes_are_info_in_code(code):
    assert emitted_severities(frozenset({code}))[code] == {"INFO"}
