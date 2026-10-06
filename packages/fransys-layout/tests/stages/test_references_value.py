"""S9: `references` returns one frozen value of decisions only, read by field name."""

from annotationlib import Format, get_annotations
from dataclasses import FrozenInstanceError, fields
from typing import Any

import pytest
from samples import connection, hid

from fransys_layout.stages.offstubs import OffEnd
from fransys_layout.stages.references import References
from fransys_layout.stages.references.digits import SetDigits
from fransys_layout.stages.references.types import Cut, MarkerDecision, PortEnd
from fransys_layout.stages.stacking import JoinedEnd, JoinedRun
from fransys_layout.stages.types import (
    LinkCase,
    LinkDecision,
    LinkMarker,
    MarkerSide,
    PortRef,
    StubText,
)

_FIELDS = (
    "joins",
    "decisions",
    "markers",
    "off_ends",
    "digits",
    "echoes",
    "connections",
    "net_groups",
)


def _value() -> References:
    """A `References` with one of everything, built by hand."""
    port = hid("port", 12)
    marker = MarkerDecision(
        connection=hid("conductor", 1),
        function=hid("function", 1),
        port=port,
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        size=(40, 8),
        partner=hid("port", 21),
        partner_set=1,
        partner_page=2,
    )
    stub = StubText(cable="-W1", far="+DB-X0", port=":1")
    ends = (
        PortEnd(ref=PortRef(function=hid("function", 1), port=port), page=(1, 1)),
        PortEnd(ref=PortRef(function=hid("function", 2), port=hid("port", 21)), page=(1, 2)),
    )
    return References(
        joins=(
            JoinedRun(
                drawing_set=1, page=1, ends=(JoinedEnd(column=("invented", "a"), port=port),)
            ),
        ),
        decisions=(
            LinkDecision(
                connection=hid("conductor", 1), a=port, b=hid("port", 21), case=LinkCase.SEVERED
            ),
        ),
        markers=(marker,),
        off_ends=(OffEnd(port=port, text=stub, carrier=None, far=hid("port", 99)),),
        digits=(SetDigits(drawing_set=1, refs=2, sheets=2),),
        echoes=(Cut(connection=hid("conductor", 1), physical_net=hid("net", 1), ends=ends),),
        connections=(connection(1, 1, 2),),
        net_groups=(),
    )


def test_the_value_holds_every_decision_by_name() -> None:
    """S9's fields, in order: joins, decisions, markers, off ends, digits, the rest."""
    # CAN-FAIL: drop `digits` from `References` (stages/references/types.py) and `_value` fails
    value = _value()
    assert tuple(one.name for one in fields(References)) == _FIELDS
    assert value.digits == (SetDigits(drawing_set=1, refs=2, sheets=2),)
    assert value.markers[0].port == hid("port", 12)


# S9 (amended 2026-09-27): what `texts` reads off the placed page, never a decision's
_PLACED = {"at", "box", "stub_extra", "shared_box", "lead", "turn", "x", "y"}
_COORDINATES = ("Point", "Box")


def _coordinates(cls: Any) -> list[str]:
    """Each field of `cls` that is a placed coordinate: by its name, or by its annotated type."""
    annotations = get_annotations(cls, format=Format.STRING)
    return [
        name
        for name in (one.name for one in fields(cls))
        if name in _PLACED or any(kind in annotations[name] for kind in _COORDINATES)
    ]


def test_a_decision_holds_no_placed_coordinate() -> None:
    """S9: `references` returns decisions only; `texts` builds every marker's geometry.

    A marker decision and the ends of a cut (a tag echo's too) carry no anchor, box, frame
    column, stub length or run box: nothing `place` has not decided yet.
    """
    # CAN-FAIL: put `at: Point` back on `MarkerDecision` (stages/references/types.py) and this
    #   fails naming `at`
    for cls in (MarkerDecision, PortEnd, Cut, References):
        assert _coordinates(cls) == [], cls.__name__
    assert _coordinates(LinkMarker) == [  # the check sees them where they are: `texts`' output
        "at",
        "box",
        "shared_box",
        "lead",
        "stub_extra",
        "turn",
    ]


def test_the_value_is_frozen_and_keyword_only() -> None:
    """No field changes after `references` returns it; a new field is one more keyword."""
    value = _value()
    with pytest.raises(FrozenInstanceError):
        value.markers = ()  # ty: ignore[invalid-assignment] -- assigning to a frozen field, testing the refusal named in the raises
    with pytest.raises(TypeError):
        References(*(getattr(value, name) for name in _FIELDS))  # ty: ignore[missing-argument] -- positional arguments to a keyword-only record, testing the TypeError
