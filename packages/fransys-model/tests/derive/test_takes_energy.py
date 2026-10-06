"""`takes_energy` and `gives_energy`: the template energy, else the kind (model-0131, 0133)."""

import pytest

from fransys_model.derive import gives_energy, takes_energy
from fransys_model.kernel import Draft, Id, Model, Origin, SchemaError, freeze, make_id
from fransys_model.vocab import Energy, Function, FunctionKind, FunctionTemplate, Item, Part
from fransys_model.vocab.enums import PartCategory

_ORIGIN = Origin(file="t.toml", line=1, note="")
_PART = ("examples", "module")


def _model(
    kind: FunctionKind, energy: Energy | None, *, templated: bool = True
) -> tuple[Model, Id]:
    draft = Draft()
    part = make_id(Part, _PART)
    item = make_id(Item, ("examples", "m1"))
    template = make_id(FunctionTemplate, (*_PART, "fn", "f"))
    draft.add(
        Part(
            id=part,
            key=_PART,
            mpn="X",
            manufacturer="M",
            description="d",
            category=PartCategory.GENERIC,
            class_code="U",
        ),
        origin=_ORIGIN,
    )
    key = (*_PART, "fn", "f")
    draft.add(
        FunctionTemplate(id=template, key=key, part=part, name="f", kind=kind, energy=energy),
        origin=_ORIGIN,
    )
    draft.add(
        Item(
            id=item,
            key=("examples", "m1"),
            part=part,
            parent=None,
            position=None,
            tag=None,
            description="",
        ),
        origin=_ORIGIN,
    )
    function = make_id(Function, ("examples", "m1", "f"))
    draft.add(
        Function(
            id=function,
            key=("examples", "m1", "f"),
            item=item,
            template=template if templated else None,
            name="f",
            kind=kind,
        ),
        origin=_ORIGIN,
    )
    return freeze(draft), function


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        (FunctionKind.LOAD, True),
        (FunctionKind.SUPPLY, False),
        (FunctionKind.COIL, False),
    ],
)
def test_the_default_is_a_load_takes_energy(kind: FunctionKind, *, expected: bool) -> None:
    """Without a declared `energy`, only `kind = load` takes energy in."""
    model, function = _model(kind, None)
    assert takes_energy(model, function) is expected


def test_a_function_without_a_template_follows_its_kind() -> None:
    """A function with no template has no fact, so its kind decides."""
    model, function = _model(FunctionKind.LOAD, None, templated=False)
    assert takes_energy(model, function) is True


@pytest.mark.parametrize(
    ("kind", "energy", "expected"),
    [
        (FunctionKind.SUPPLY, Energy.IN, True),
        (FunctionKind.LOAD, Energy.OUT, False),
    ],
)
def test_a_declared_energy_overrides_the_kind(
    kind: FunctionKind, energy: Energy, *, expected: bool
) -> None:
    """A supply declared `in` takes energy; a load declared `out` does not."""
    model, function = _model(kind, energy)
    assert takes_energy(model, function) is expected


def test_energy_on_a_coil_is_refused() -> None:
    """Only a supply or a load has an energy direction."""
    with pytest.raises(SchemaError):
        _model(FunctionKind.COIL, Energy.IN)


@pytest.mark.parametrize(
    ("kind", "energy", "templated", "gives", "takes"),
    [
        (FunctionKind.LOAD, Energy.OUT, True, True, False),
        (FunctionKind.SUPPLY, Energy.IN, True, False, True),
        (FunctionKind.SUPPLY, None, False, True, False),
        (FunctionKind.LOAD, None, False, False, True),
        (FunctionKind.COIL, None, False, False, False),
    ],
)
def test_gives_energy_reads_the_template_else_a_supply_kind(
    kind: FunctionKind, energy: Energy | None, *, templated: bool, gives: bool, takes: bool
) -> None:
    """`gives_energy` is its own fact, not `takes_energy` negated: a coil does neither."""
    model, function = _model(kind, energy, templated=templated)
    assert gives_energy(model, function) is gives
    assert takes_energy(model, function) is takes
