"""A removed item marks its nearest drawn ancestor on the overview page (OVERVIEW RC1 to RC5).

The two-release plant is the units worked example plus a yard switch `-K7` with a connector child
`-P7`, and a device `-K9`; release 2 drops `-P7` and `-K9`. Each test
names what breaks it.
"""

import dataclasses
import json
import re
from functools import cache
from typing import Any

import fransys as fr
import fransys_parts
from _model_build_cover import system_document
from fransys_overview import html
from test_units_worked_example import _system_design

from fransys_layout.engines.overview import lay_out_overview
from fransys_model.derive.baseline import diff, dumps, listing, loads

_HOST = "=YARD+YARD-K7"
_CHILD = "=YARD+YARD-P7"
_DEVICE = "=YARD+YARD-K9"


def _plant(*, child: bool, device: bool) -> Any:
    parts = fransys_parts.load("demo_parts")
    design, field1, _field2 = _system_design(parts)
    yard = design.location("YARD", "Yard")
    group = design.group("YARD", "Yard wiring")
    wire = design.wiring(colour="BU", gauge="0.5")
    host = design.item("DEMO-SWITCH-2P", tag="K7", at=yard, group=group)
    wire(field1[0].outer, host.fn("x1")["1"])
    if child:
        design.item("DEMO-CONN-2P", tag="P7", parent=host, at=yard, group=group)
    if device:
        wire(field1[1].outer, design.item("DEMO-SWITCH-2P", tag="K9", at=yard, group=group)["1"])
    return fr.build(parts, design.draft(), system_document()).model


@cache
def _releases() -> tuple[Any, Any]:
    return listing(_plant(child=True, device=True), None), _plant(child=False, device=False)


def _page(previous: Any) -> dict[str, Any]:
    model = _releases()[1]
    shown = html(lay_out_overview(model)[0], changes=diff(previous, listing(model, None)))
    found = re.search(r'id="overview-data">(.*?)</script>', shown, re.DOTALL)
    assert found is not None
    return json.loads(found.group(1))


def _marked_texts(data: dict[str, Any]) -> dict[str, str]:
    """`{box text: kind}` over every view."""
    found: dict[str, str] = {}
    for view, (boxes, _lines) in zip(data["views"], data["changes"]["views"], strict=True):
        for at, kind in boxes:
            found[view["boxes"][at]["lines"][0]] = kind
    return found


def test_a_removed_child_marks_its_host_and_a_parentless_device_stays_listed() -> None:
    """Breaks if the host box is not marked changed, or `-K9` (no parent) leaves the list."""
    data = _page(_releases()[0])
    assert _marked_texts(data) == {"Field devices (2)": "changed"}
    rest = data["changes"]["rest"]
    assert ["removed", _DEVICE] in rest
    assert ["removed", _CHILD] not in rest


def _without_parent(old: Any) -> Any:
    return dataclasses.replace(
        old, items=tuple(dataclasses.replace(row, parent=None) for row in old.items)
    )


def test_a_listing_written_before_the_parent_field_loads_with_its_bytes() -> None:
    """Breaks if `loads` needs `parent`, or `dumps` writes it off its default."""
    old = _releases()[0]
    assert '"parent"' in dumps(old)
    bare = _without_parent(old)
    text = dumps(bare)
    assert '"parent"' not in text
    assert loads(text) == bare
    assert dumps(loads(text)) == text


def test_the_removed_items_of_a_pre_parent_listing_stay_list_only() -> None:
    """Breaks if a removed item of a listing without `parent` marks a box."""
    data = _page(_without_parent(_releases()[0]))
    assert _marked_texts(data) == {}
    assert ["removed", _CHILD] in data["changes"]["rest"]


def test_a_listed_item_names_its_parent_by_its_printed_designation() -> None:
    """Breaks if a child's parent is not its host's designation, or a root names one."""
    rows = {row.designation: row for row in _releases()[0].items}
    assert rows[_CHILD].parent == _HOST
    assert rows[_HOST].parent is None
