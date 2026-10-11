"""Findings of one code list in natural designation order, `-X2` before `-X10` (decision 0135)."""

import fransys as fr
from fransys.pipeline import _resolved

from fransys_model.kernel import Draft, Finding, Origin, Severity, freeze, make_id
from fransys_model.vocab.core import Item

_ORIGIN = Origin(file="packages/fransys/tests/test_findings_order.py", line=1, note="invented")


def _item(tag: str) -> Item:
    return Item(
        id=make_id(Item, ("item", tag)),
        key=("item", tag),
        part=None,
        parent=None,
        position=None,
        tag=tag,
        description="Invented",
    )


def test_findings_of_one_code_list_by_natural_designation_not_by_id():
    items = [_item(f"X{n}") for n in (10, 2, 11, 1, 3, 9, 12, 4)]
    draft = Draft()
    draft.extend(items, origin=_ORIGIN)
    model = freeze(draft)
    findings = tuple(
        Finding(code="ITEM_WITHOUT_PART", severity=Severity.INFO, subjects=(i.id,), message="m")
        for i in items
    )

    printed = [fr.derive.item_designation(model, f.subjects[0]) for f in _resolved(findings, model)]

    assert printed == ["X1", "X2", "X3", "X4", "X9", "X10", "X11", "X12"]
