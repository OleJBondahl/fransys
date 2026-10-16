"""Tests: the unit-box sites of EL-2 give the same output before and after they read roles.

Each test pins what a derive module printed on a planted model when the sites still read
`Id.kind` and the item and function kinds (model-0297). The modules are `kinds`, `view_rollup`,
`bom`, `block_diagram`, `finding_names` and `order`. `marker_targets` and `page_nav` read
`ItemKind.TERMINAL`, which no role field carries, and are not switched, so they are not pinned.
"""

from typing import Any, cast

import pytest
from plant import Plant
from roles_plants import roles_plant

from fransys_model.derive.block_diagram import box_dashed, box_lines
from fransys_model.derive.bom import bom_lines
from fransys_model.derive.finding_names import name_of, subject_text
from fransys_model.derive.kinds import item_kind
from fransys_model.derive.order import finding_order_key
from fransys_model.derive.rows_overview_view import ViewBox, ViewLine, ViewRows
from fransys_model.derive.view_rollup import subject_marks, view_lookup
from fransys_model.kernel import Finding, Id, SchemaError, Severity
from fransys_model.layout import BoxKey, OverviewMode, OverviewRef, OverviewRefKind
from fransys_model.vocab.enums import ConductorKind, FunctionKind, ItemKind
from fransys_model.vocab.tables import functions
lazy from fransys_model.vocab.core import Item

ROLES_MODEL, ROLES_IDS = roles_plant()
_PLANT = Plant()
UNIT = _PLANT.unit("u1", tag="U1")
ITEM_A = _PLANT.item("a", designation="-K1", unit=UNIT)
FUNCTION_A = _PLANT.function(ITEM_A, "fa", kind=FunctionKind.COIL)
PORT_A = _PLANT.port(FUNCTION_A, "A1")
ITEM_B = _PLANT.item("b", designation="-Q1", unit=UNIT)
PORT_B = _PLANT.port(_PLANT.function(ITEM_B, "fb", kind=FunctionKind.GENERIC), "1")
WIRE = _PLANT.wire(PORT_A, PORT_B, key="w", kind=ConductorKind.WIRE)
MODEL = _PLANT.model()
MISTYPED_SCOPE = "a BOM scope is an item or a location node of the model"


def test_item_kind_of_every_planted_item() -> None:
    """The decider names strip, terminal, connector, bar and cable; the rest are devices."""
    found = {k: item_kind(ROLES_MODEL, v).name for k, v in ROLES_IDS.items() if k[:5] == "item:"}
    assert {k: v for k, v in found.items() if v != "DEVICE"} == {
        "item:strip": "STRIP",
        "item:terminal_1": "TERMINAL",
        "item:terminal_2": "TERMINAL",
        "item:connector": "CONNECTOR",
        "item:bar": "BAR",
        "item:cable": "CABLE",
    }
    assert item_kind(MODEL, ITEM_A) is ItemKind.DEVICE


def test_a_connector_function_makes_a_connector_item_only_when_all_are() -> None:
    """The one connector function of the planted item decides `CONNECTOR`."""
    held = functions(ROLES_MODEL)[ROLES_IDS["connector"]]
    assert held.kind is FunctionKind.CONNECTOR
    assert item_kind(ROLES_MODEL, held.item) is ItemKind.CONNECTOR


def _key(ref: OverviewRef) -> BoxKey:
    return BoxKey(ref=ref)


def _rows() -> ViewRows:
    a = _key(OverviewRef(kind=OverviewRefKind.ITEM, item=ITEM_A))
    b = _key(OverviewRef(kind=OverviewRefKind.ITEM, item=ITEM_B))
    unit = _key(OverviewRef(kind=OverviewRefKind.UNIT, unit=UNIT))
    return ViewRows(
        unit=None,
        level=None,
        mode=OverviewMode.PLAIN,
        open=None,
        boxes=tuple(ViewBox(key=k, lines=("x",), dashed=False) for k in (a, b, unit)),
        lines=(ViewLine(a=a, b=b, kind="wire", via=None, strip=None, text="t"),),
    )


def test_view_lookup_keys_each_box_by_its_kind_text() -> None:
    """The lookup keys are `("item", id)` and `("unit", id)` in drawing order."""
    assert view_lookup(MODEL, _rows()) == {
        ("item", ITEM_A): 0,
        ("item", ITEM_B): 1,
        ("unit", UNIT): 2,
    }


def test_subject_marks_by_subject_kind() -> None:
    """Item, function and port count on the item box; a conductor on its line; a unit on its own."""
    rows = _rows()
    lookup = view_lookup(MODEL, rows)
    got = {n: subject_marks(MODEL, rows, lookup, s) for n, s in _subjects().items()}
    assert got == {
        "item": ((0,), ()),
        "function": ((0,), ()),
        "port": ((0,), ()),
        "conductor": ((), (0,)),
        "unit": ((2,), ()),
    }


def _subjects() -> dict[str, Id[Any]]:
    return {
        "item": ITEM_A,
        "function": FUNCTION_A,
        "port": PORT_A,
        "conductor": WIRE,
        "unit": UNIT,
    }


def test_bom_scope_item_and_unit_and_the_raise_on_any_other_kind() -> None:
    """An item and a unit scope give no line (no part); a conductor or a net scope raises."""
    assert bom_lines(MODEL, ITEM_A) == ()
    assert bom_lines(MODEL, UNIT) == ()
    for model, bad in ((MODEL, WIRE), (ROLES_MODEL, ROLES_IDS["net_power"])):
        with pytest.raises(SchemaError, match=MISTYPED_SCOPE):
            bom_lines(model, cast("Id[Item]", bad))


def test_bom_unit_scope_of_a_missing_unit_raises() -> None:
    """A unit id the model does not hold raises through `require`."""
    other = Plant()
    missing = other.unit("gone")
    with pytest.raises(SchemaError, match="not a unit of the model"):
        bom_lines(MODEL, missing)


def test_block_diagram_box_lines_and_dash() -> None:
    """A unit box prints its tag then its title; an item box prints its designation."""
    assert box_lines(MODEL, UNIT, None) == ("-U1", "unit rev 1.1")
    assert box_dashed(MODEL, UNIT, None) is False
    assert box_lines(MODEL, ITEM_A, None) == ("-U1--K1",)
    assert box_dashed(MODEL, ITEM_A, None) is False


def test_finding_names_by_subject_kind() -> None:
    """Each kind with a namer prints its text; a kind without one prints its kind."""
    assert name_of(MODEL, ITEM_A) == "-U1--K1"
    assert name_of(MODEL, FUNCTION_A) == "-U1--K1"
    assert name_of(MODEL, PORT_A) == "-U1--K1:A1"
    assert name_of(MODEL, WIRE) == "-U1--K1:A1 -U1--Q1:1"
    assert name_of(MODEL, UNIT) == "unit -U1"
    assert subject_text(MODEL, WIRE) == "wire -U1--K1:A1 to -U1--Q1:1"
    assert subject_text(MODEL, ITEM_A) == "-U1--K1"
    assert subject_text(ROLES_MODEL, ROLES_IDS["net_power"]) == name_of(
        ROLES_MODEL, ROLES_IDS["net_power"]
    )


def test_finding_order_key_reads_an_item_or_a_port_and_skips_the_rest() -> None:
    """An item and a port give a natural key; a function, conductor or unit sorts after them."""

    def key(subject: Id[Any]) -> tuple[int, object]:
        finding = Finding(code="X", severity=Severity.WARNING, message="m", subjects=(subject,))
        return finding_order_key(MODEL, finding)

    assert key(ITEM_A)[0] == 0
    assert key(PORT_A)[0] == 0
    assert [key(s) for s in (FUNCTION_A, WIRE, UNIT)] == [(1, ())] * 3
