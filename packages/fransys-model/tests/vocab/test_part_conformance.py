"""Tests: the `part_conformance` validator."""

import dataclasses
from typing import Any

import pytest
from examples import bundle_records, relay_part_bundle

from fransys_model.kernel import (
    Draft,
    Finding,
    Id,
    Model,
    Origin,
    Record,
    Severity,
    freeze,
    make_id,
)
from fransys_model.vocab.core import Item, Port
from fransys_model.vocab.instantiate import PartBundle, instantiate
from fransys_model.vocab.validators.part_conformance import (
    ITEM_PART_MISMATCH,
    ITEM_WITHOUT_PART,
    check_part_conformance,
)

_KEY = ("examples", "relay-1")


def _freeze(records: tuple[Record, ...]) -> Model:
    draft = Draft()
    draft.extend(records, origin=Origin(file="test_part_conformance.py", line=1, note="fixture"))
    return freeze(draft)


def _relay(**kwargs: Any) -> tuple[Record, ...]:
    return instantiate(relay_part_bundle(), _KEY, **kwargs)


def _the[R](records: tuple[Record, ...], record_type: type[R], name: str) -> R:
    """The one `record_type` record called `name`."""
    (found,) = [
        r for r in records if isinstance(r, record_type) and getattr(r, "name", None) == name
    ]
    return found


def _without(records: tuple[Record, ...], *dropped: Record) -> tuple[Record, ...]:
    return tuple(r for r in records if r not in dropped)


def _with(records: tuple[Record, ...], old: Record, new: Record) -> tuple[Record, ...]:
    return tuple(new if r is old else r for r in records)


def _mismatches(records: tuple[Record, ...], bundle: PartBundle | None = None) -> list[Finding]:
    bundle = relay_part_bundle() if bundle is None else bundle
    model = _freeze((*bundle_records(bundle), *records))
    return [f for f in check_part_conformance(model) if f.code == ITEM_PART_MISMATCH]


ITEM_ID = make_id(Item, _KEY)


def _subjects(*ids: Id[Any]) -> tuple[Id[Any], ...]:
    """What a `Finding` stores: each id once, in id order."""
    return tuple(sorted(ids))


def _partless(key: str, *, parent: Id[Item] | None = None, external: bool = False) -> Item:
    return Item(
        id=make_id(Item, ("examples", key)),
        key=("examples", key),
        part=None,
        parent=parent,
        position=None,
        tag=None,
        description="",
        external=external,
    )


def test_a_part_less_external_item_and_its_children_give_no_item_without_part() -> None:
    """The flag on a strip or a parent silences the item; a plain part-less item fires."""
    strip = _partless("x8", external=True)
    terminal = _partless("x8-1", parent=strip.id)
    plain = _partless("plain")
    findings = check_part_conformance(_freeze((strip, terminal, plain)))
    assert [f.subjects for f in findings if f.code == ITEM_WITHOUT_PART] == [(plain.id,)]


# ---- each discrepancy is one finding, about the right records ---------------------------


def _marked_bundle() -> PartBundle:
    """The relay part whose `A1` pin prints `"1"` (decision model-0053)."""
    bundle = relay_part_bundle()
    a1 = next(t for t in bundle.port_templates if t.name == "A1")
    marked = tuple(
        dataclasses.replace(t, marking="1") if t is a1 else t for t in bundle.port_templates
    )
    return dataclasses.replace(bundle, port_templates=marked)


@pytest.mark.parametrize("marking", ["X", "", None], ids=["other", "empty", "none"])
def test_a_marking_that_differs_from_the_template_is_one_finding(marking: str | None) -> None:
    """Editing a port's marking away from its template's is one finding naming `marking`."""
    bundle = _marked_bundle()
    records = instantiate(bundle, _KEY)
    a1 = _the(records, Port, "A1")
    (finding,) = _mismatches(_with(records, a1, dataclasses.replace(a1, marking=marking)), bundle)
    assert finding.severity is Severity.ERROR
    assert finding.subjects == _subjects(ITEM_ID, a1.id)
    assert finding.message.endswith(" in marking")


# ---- items without a part ----------------------------------------------------------------


# ---- what every finding looks like -------------------------------------------------------
