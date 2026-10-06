"""A public-surface docstring never cites a spec or decision id (FR7: the API text reads alone).

Covers every name in `fransys.__all__` and `fransys_model.derive.__all__`.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("fransys_lean_api_ids", ROOT / "scripts/lean_api.py")
assert _SPEC is not None
assert _SPEC.loader is not None
lean_api = importlib.util.module_from_spec(_SPEC)
sys.modules["fransys_lean_api_ids"] = lean_api
_SPEC.loader.exec_module(lean_api)

_ID_SHAPES = (
    (
        r"\(\s*(?:(?:baseline |units |facade |root |model )?spec |root )?"
        r"(?:[A-Z]{1,3}\d+[a-z]?)(?:[ ,./]+(?:[A-Z]{1,3})?\d+[a-z]?)*\s*\)"
    ),
    r"\b[Dd]ecisions? (?:\w+-)?\d{4}",
    r"\b[a-z]+-\d{4}\b",
    r"\b[A-Z]{1,3}\d+\.\d+\b",
    r"\bS\d+ M\d+\b",
    r"\bowner 20\d\d",
    r"\b[Ss]pec\b",
    r"\bDESIGN \d",
    r"\b(?:EN|FD|FS|FR|MS|RW|EA|GUIDE)\d+\b",
    r"\b(?:spec|specs) [A-Z]{1,3}\d+\b",
    r"\b[A-Z]{1,3}\d+(?:, [A-Z]{1,3}\d+)+ ?\)",
    r"\bUNIT-(?:ID|TAGS)\b",
    r"\bUT\d\b",
    r"\bI\d\b",
    r"\bdesign/\w+\.md",
    r"\bboard-unit ruling",
)
ID_RE = re.compile("|".join(_ID_SHAPES))


def _hits() -> list[str]:
    """`name: line` for each surface docstring line holding an id."""
    surface = lean_api.lean_surface
    found = []
    for module in ("fransys", "fransys_model.derive"):
        for entry in surface.resolve_surface_names((module,)):
            node = surface.find_def(surface.module_tree(entry.defining_file), entry.qualname)
            doc = surface.literal_docstring(node)
            if doc is None:
                continue
            found += [
                f"{entry.name}: {x.strip()}" for x in doc.value.splitlines() if ID_RE.search(x)
            ]
    return found


def test_surface_docstrings_cite_no_spec_or_decision_id():
    """No surface docstring holds `(FD5)`, `decision 0033`, `model-0121`, `(units spec U3)` ..."""
    assert _hits() == []


def test_the_id_pattern_matches_each_shape_the_sweep_removed():
    """The pattern can fail: it matches every id shape the sweep targeted."""
    samples = [
        "reads from the root (FD5); none",
        "(decision model-0042)",
        "see decision 0033",
        "built once (model-0108)",
        "(units spec U3, U8)",
        "(baseline spec L1)",
        "(L4, R2)",
        "(layout-0107)",
        "(spec F5)",
        "S20 M1 rule",
        "root DESIGN 9",
        "(UNIT-ID I1), default",
        "numbers from (`U`, UT3)",
        "the sole root, I4's amendment",
        "(design/facets.md)",
        "(the board-unit ruling)",
    ]
    assert [s for s in samples if not ID_RE.search(s)] == []
    assert not ID_RE.search("a Q1 coil on strip -X1, `L1:10` sorts after `L1:2`")
