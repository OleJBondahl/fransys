"""RW4's "one place" ruling (decision model-0108, `docs/archive/specs/2026-09-26-repeated-work.md`):
every reader switches to `is_cable`/`cable_items` (`fransys_model.vocab.cables`), and none
keeps its own copy of the old test, checked with stdlib `ast` the way `tests/test_boundaries.py`
checks import layering.

The old test was a full scan, `facets_of(model, CableFacet)`, used to decide "is this item a
cable." The one place that scan is still legitimate is `derive/harness.py`'s `_facts_of`: it
reads a cable's own installed length (`facet.length_mm`), a fact about an item already known to
be a cable, never a type test. Every other occurrence of that exact call shape, anywhere in
`packages/*/src`, is a second copy of the rule root `CLAUDE.md`'s own red flag names ("one rule
computed in two places... drifts from the first") -- this test fails on any of them, including
one that creeps back into `harness.py` itself (a reader re-added there would make its own count
more than the one line this test allows).
"""

import ast
from pathlib import Path

PACKAGES_ROOT = Path(__file__).resolve().parent.parent / "packages"
_HARNESS_PY = PACKAGES_ROOT / "fransys-model" / "src" / "fransys_model" / "derive" / "harness.py"


def _cable_facet_scan_lines(path: Path) -> list[int]:
    """Line numbers of every `facets_of(<anything>, CableFacet)` call in `path`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "facets_of"
        and any(isinstance(arg, ast.Name) and arg.id == "CableFacet" for arg in node.args)
    ]


def test_no_reader_rescans_cablefacet_to_decide_cable_ness():
    """A `facets_of(model, CableFacet)` call anywhere outside `harness.py`'s one installed-
    length line is a second, independently-maintained copy of "is this a cable" -- exactly what
    `is_cable`/`cable_items` replaced. `harness.py` itself must show exactly one such call (a
    rise there means a switched reader crept back to the old scan, same as anywhere else)."""
    offenders: dict[Path, list[int]] = {}
    for path in sorted(PACKAGES_ROOT.glob("*/src/**/*.py")):
        lines = _cable_facet_scan_lines(path)
        if not lines:
            continue
        if path == _HARNESS_PY:
            assert len(lines) == 1, (
                f"harness.py should have exactly one facets_of(model, CableFacet) call (its own "
                f"installed-length read), found {len(lines)} at lines {lines}"
            )
            continue
        offenders[path] = lines
    assert offenders == {}
