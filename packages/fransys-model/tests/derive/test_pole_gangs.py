"""Tests: `pole_gangs` names the groups drawn as one symbol, their lead and each port's pole."""

from plant import Plant

from fransys_model.derive import pole_gangs
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import PoleGroup
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Port


def _model(
    *, selector: bool = False
) -> tuple[Model, tuple[Id[Function], ...], tuple[Id[Port], ...]]:
    plant = Plant()
    item = plant.item("q1", part=plant.part("Q"))
    poles = tuple(plant.function(item, name) for name in ("p1", "p2", "p3"))
    ports = tuple(plant.port(function, "1") for function in poles)
    group = PoleGroup(id=make_id(PoleGroup, ("g",)), key=("g",), functions=poles, selector=selector)
    draft = Draft()
    draft.extend(plant.records, origin=Origin(file="t.py", line=1, note="x"))
    draft.extend([group], origin=Origin(file="t.py", line=2, note="x"))
    return freeze(draft), poles, ports


def test_a_drawn_group_has_lead_members_and_a_pole_per_port() -> None:
    """Member k's port is pole k; the first member leads."""
    model, poles, ports = _model(selector=True)
    (gang,) = pole_gangs(model, frozenset(poles))
    assert gang.lead == poles[0]
    assert gang.members == poles
    assert gang.poles == 3
    assert gang.selector
    assert [(e.port, e.pole) for e in gang.pole_of] == list(zip(ports, range(3), strict=True))


def test_a_group_with_an_undrawn_member_has_no_row() -> None:
    """Each drawn member then draws alone."""
    model, poles, _ = _model()
    assert pole_gangs(model, frozenset(poles[:2])) == ()
