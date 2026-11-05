"""The "one place" ruling (decision model-0108):
every reader switches to `is_cable`/`cable_items` (`fransys_model.derive.facts.item_predicates`),
and none keeps its own copy of the old test, checked with stdlib `ast` the way
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
