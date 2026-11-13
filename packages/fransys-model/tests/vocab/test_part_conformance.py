"""Tests: the `part_conformance` validator."""

import dataclasses
from pathlib import Path
from typing import Any

import fransys_parts
import pytest
from current_plant import device
from examples import bundle_records, relay_part_bundle
from fransys_author.design import Design as EngineDesign
from fransys_author.instantiate import instantiate
from fransys_author.surface.design import Design
from plant import Plant

from fransys_model.checks.part_conformance import (
    ITEM_PART_MISMATCH,
    ITEM_WITHOUT_PART,
    PART_POLE_WITHOUT_SIDE,
    check_part_conformance,
)
from fransys_model.elecdef import LinkKind
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
    merge,
)
from fransys_model.vocab.core import Item, Port
from fransys_model.vocab.enums import FunctionKind, PartCategory
from fransys_model.vocab.tables import function_templates, parts
lazy from fransys_model.vocab.instantiate import PartBundle

_KEY = ("examples", "relay-1")
_FIELD_DATA = Path(__file__).parents[4] / "tests/field_cases/data"


def _freeze(records: tuple[Record, ...]) -> Model:
    draft = Draft()
    draft.extend(records, origin=Origin(file="test_part_conformance.py", line=1, note="fixture"))
    return freeze(draft)


def _relay(**kwargs: Any) -> tuple[Record, ...]:
    return instantiate(relay_part_bundle(), _KEY, **kwargs)


def _the[R](records: tuple[Record, ...], record_type: type[R], name: str) -> R:
    """The one `record_type` record called `name`."""
    (found,) = [r for r in records if isinstance(r, record_type) and getattr(r, "name", None) == name]
    return found


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
    marked = tuple(dataclasses.replace(t, marking="1") if t is a1 else t for t in bundle.port_templates)
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


# ---- a protecting function's conductive link needs sides (R2051) ---------------------------


def _pole_codes(*, kind: FunctionKind, sided: bool) -> list[Finding]:
    plant = Plant()
    device(plant, "F", kind=kind, link=LinkKind.CONDUCTIVE, sided=sided)
    return [f for f in check_part_conformance(plant.model()) if f.code == PART_POLE_WITHOUT_SIDE]


def test_a_sideless_conductive_link_of_a_protecting_function_is_an_error() -> None:
    """A protection with unsided pins fires; sided pins, a feedthrough and a non-protecting function stay clean."""
    (found,) = _pole_codes(kind=FunctionKind.PROTECTION, sided=False)
    assert found.severity is Severity.ERROR
    assert "function 'f' of part" in found.message
    assert found.fix.startswith("state side = line/load on its pins")
    assert _pole_codes(kind=FunctionKind.PROTECTION, sided=True) == []
    assert _pole_codes(kind=FunctionKind.GENERIC, sided=False) == []
    assert _pole_codes(kind=FunctionKind.TERMINAL, sided=False) == []


@pytest.mark.parametrize("library", ["demo_parts", *sorted(p.name for p in (_FIELD_DATA).iterdir() if p.is_dir())])
def test_every_demo_and_field_case_part_states_its_poles_sides(library: str) -> None:
    """No part of the demo library or of a field-case data set trips the check (it would break `fr.write`)."""
    root = _FIELD_DATA / library
    draft = fransys_parts.load(library) if library == "demo_parts" else fransys_parts.load_path(root)
    engine = EngineDesign(draft)
    strips = Design(draft, scope=engine)
    templates = function_templates(freeze(draft))
    for number, part in enumerate(parts(freeze(draft)).values()):
        if part.category is PartCategory.TERMINAL and any(t.part == part.id and t.kind is FunctionKind.TERMINAL for t in templates.values()):
            strips.terminal_strip(f"X{number}", part.mpn, 1).run("L", 1)
        else:
            engine.item(part.mpn, name=f"i{number}")
    model = freeze(merge(draft, engine.draft()))
    assert [f for f in check_part_conformance(model) if f.code == PART_POLE_WITHOUT_SIDE] == []
