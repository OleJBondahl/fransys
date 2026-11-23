"""Every code only the core emits has its `CodeInfo` in `fransys_el.FINDING_CODES` (layout-0358)."""

import re
from pathlib import Path
from typing import get_args

from fransys_el import FINDING_CODES

import fransys_layout.core as core_pkg
from fransys_model.kernel import Severity

_CORE_ONLY = [
    "MARKER_UNPLACED",
    "CONNECTION_NOT_ACCOUNTED",  # CORE-ACCOUNT (R2650): the core says it after its last round
    "LABEL_NO_ROOM",
    "OUTLINE_NO_ROOM",
    "ALIGN_DROPPED",
    "CARD_OVERFULL",
    "WIRE_THROUGH_BODY",
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
    "TAG_ACROSS_BODY",  # CROSS-HALF-TAGS (el-0081, R812): the core says it, el registers the row
]
_EL_ONLY = [
    "UNKNOWN_SYMBOL_KEY",  # el emits it where it picks the key (el-0039)
    "DRAWING_SET_REFUSED",  # el emits it beside the ERROR that refused a set (R3155)
    "PLACEMENT_PROBLEM",  # el raises it from a ProblemError or a failed set (el-0051)
    "SYMBOL_PORT_MISSING",  # el raises it from a PortMissingError (decision 0018)
    "OVERLAP",  # DRAWING-INVARIANTS: el emits it over the finished drawings
    "OUT_OF_PAGE",
    "WHERE_TEXT_FAR",
    "WIRE_OVER_MARKER",  # MARKER-FREE-SIDE: el counts what meets a marker box
    "NOT_SERIES_PARALLEL",  # el emits it for a bridge of derive.series_parallel (0364)
    "CONNECTION_NOT_DRAWN",  # DRAWN-NETLIST (el-0052): el checks the finished drawings
    "DANGLING_WIRE_END",  # DRAWN-NETLIST (el-0086): a wire end that meets nothing
    "DRAWING_SHORTS_NETS",
    "INK_WITHOUT_CONDUCTOR",  # CONDUCTOR-INK (CP-S2c-2): el reads the drawn ink against the conductors of the model
    "CONNECTION_DRAWN_TWICE",
    "WIRE_NOT_ORTHOGONAL",
    "MISSING_JUNCTION_DOT",
    "POWER_SYMBOL_NOT_JOINED",
    "POWER_SYMBOL_WRONG_KIND",
    "RAIL_IDENTITY_SHARED",
    "PRINTED_TEXT_WRONG",
    "REFERENCE_NOT_READABLE",
    "DOT_ON_CROSSING",
    "WIRE_OVER_PIN_TIP",
    "HARNESS_WIRE_MISMATCH",  # PROOF-S5 (el-0122): el compares the cable block with the harness-wire rows
    "DRAWN_READ_INCOMPLETE",  # el-0137: el reports a set the drawn-page checks did not read
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


def test_a_drawn_short_a_trunk_through_a_body_and_a_page_overflow_are_errors():
    """Stocks are 0 on all seven builds, so each is an ERROR (el-0052, R452; layout-0394, R492; CUT-TALL step 1)."""
    for code in ("DRAWING_SHORTS_NETS", "WIRE_THROUGH_BODY", "PAGE_OVERFLOW"):
        info = next(i for i in FINDING_CODES if i.code == code)
        assert info.severity is Severity.ERROR, code


def test_a_net_function_lane_wire_set_page_or_print_left_out_is_an_error():
    """The five codes of a dropped drawing item and eight defect codes are all 0 on the seven builds and field cases: ERROR (L1, R582; L1b, R700)."""
    from fransys_model.vocab import FINDING_CODES as MODEL_CODES

    wanted = {"NET_NOT_DRAWN", "FUNCTION_NOT_DRAWN", "LANE_WIRE_DROPPED", "SET_WITHOUT_PAGE", "UNPRINTED_SET", "NO_BLOCK"}
    wanted |= {
        "CONNECTION_DRAWN_TWICE",
        "WIRE_NOT_ORTHOGONAL",
        "MISSING_JUNCTION_DOT",
        "WIDER_THAN_PAGE",
        "DRAWN_READ_INCOMPLETE",
    }
    from fransys_layout import FINDING_CODES as LAYOUT_CODES

    held = {info.code: info.severity for info in (*MODEL_CODES, *LAYOUT_CODES, *FINDING_CODES)}
    assert {code: held[code] for code in wanted} == dict.fromkeys(wanted, Severity.ERROR)


def test_a_card_spill_is_an_info_because_tag_pairs_join_it() -> None:
    """CARD_OVERFULL states a spill joined by tag pairs and loses no fact (R1154)."""
    info = next(i for i in FINDING_CODES if i.code == "CARD_OVERFULL")
    assert info.severity is Severity.INFO


def test_a_shared_name_fix_names_the_fuse_for_a_supply_and_the_bond_or_the_units_for_a_ground():
    """R1976, R2589: RAIL_IDENTITY_SHARED names a protective device for a supply name, and for a ground a bond or the declaring units."""
    fix = next(i for i in FINDING_CODES if i.code == "RAIL_IDENTITY_SHARED").fix
    assert fix.startswith("No call clears this:")
    assert "put a fuse or breaker between them" in fix
    assert "For a ground: bond the nets, or declare each supply in its own unit" in fix
