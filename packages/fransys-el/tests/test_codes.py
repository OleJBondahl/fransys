"""Every code only the core emits has its `CodeInfo` in `fransys_el.FINDING_CODES` (layout-0358)."""

import re
from pathlib import Path
from typing import get_args

from fransys_el import FINDING_CODES

import fransys_layout.core as core_pkg

_CORE_ONLY = [
    "MARKER_UNPLACED",
    "ANNEX_UNPLACED",
    "ALIGN_DROPPED",
    "CARD_OVERFULL",
    "PAGE_OVERFLOW",
    "FILL_UNDER_MIN",
    "HEAD_OFF_LEGS",
    "NO_CELL",
    "LANE_WIRE_DROPPED",
    "NO_BLOCK",
    "BLOCK_NOT_PLACED",
    "CHAIN_REFUSED",
    "WIDER_THAN_PAGE",
    "WIRE_MEETS_NET",
]
_EL_ONLY = [
    "UNKNOWN_SYMBOL_KEY",  # el emits it where it picks the key (el-0039)
    "PLACEMENT_PROBLEM",  # el raises it from a ProblemError or a failed set (el-0051)
    "OVERLAP",  # DRAWING-INVARIANTS: el emits it over the finished drawings
    "OUT_OF_PAGE",
    "NOT_SERIES_PARALLEL",  # el emits it for a bridge of derive.series_parallel (0364)
    "CONNECTION_NOT_DRAWN",  # DRAWN-NETLIST (el-0052): el checks the finished drawings
    "DRAWING_SHORTS_NETS",
    "ROUTE_WRONG_PORT",
    "MARKER_UNPAIRED",
    "CONNECTION_DRAWN_TWICE",
    "WIRE_NOT_ORTHOGONAL",
    "MISSING_JUNCTION_DOT",
]


def test_the_core_only_codes_are_registered_here():
    assert sorted(info.code for info in FINDING_CODES) == sorted([*_CORE_ONLY, *_EL_ONLY])


def test_every_core_only_code_appears_in_the_core_source():
    text = "".join(p.read_text() for p in Path(core_pkg.__file__).parent.glob("*.py"))
    for code in _CORE_ONLY:
        assert re.search(rf"\b{code}\b", text), code


def test_every_code_the_core_can_emit_is_registered_for_the_mapper():
    """`kernel_findings` refuses an unregistered code, so each `FindingCode` needs a row."""
    from fransys_layout import FINDING_CODES as LAYOUT_CODES
    from fransys_layout.core.values import FindingCode

    held = {info.code for info in (*LAYOUT_CODES, *FINDING_CODES)}
    # LANE_TURNED is typed but never emitted; test_write pins that the mapper refuses it
    assert sorted(set(get_args(FindingCode)) - held - {"LANE_TURNED"}) == []


def test_a_drawn_short_and_a_wrong_port_are_errors():
    """Both stocks are 0 on all seven builds, so each code is an ERROR (el-0052, R452)."""
    from fransys_model.kernel import Severity

    for code in ("DRAWING_SHORTS_NETS", "ROUTE_WRONG_PORT"):
        info = next(i for i in FINDING_CODES if i.code == code)
        assert info.severities == (Severity.ERROR,), code


def test_page_overflow_is_an_error():
    """A column or row over the page is a refusal, never a warning (CUT-TALL step 1)."""
    from fransys_model.kernel import Severity

    info = next(i for i in FINDING_CODES if i.code == "PAGE_OVERFLOW")
    assert info.severities == (Severity.ERROR,)
