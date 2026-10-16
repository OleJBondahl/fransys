"""Symbol ids are Id text (S1); pin names come from the Pick's ports."""

import dataclasses
import re

import pytest
from fransys_el.placement_ids import pin_names, symbol_ids
from fransys_el.placement_kit import ProblemError
from placement_fixtures import kit_for, planted_model

from fransys_layout.core import PinRef
from fransys_model.derive import item_designation
from fransys_model.kernel import render_id
from fransys_model.vocab import functions, ports


def _function_named(model, name):
    """The one function of `model` whose name is `name`."""
    return next(f for f, record in functions(model).items() if record.name == name)


def test_symbol_ids_are_the_id_text_and_unique() -> None:
    """Each symbol id is its function Id's text (S1), never a printed designation; all unique."""
    model = planted_model()
    kit = kit_for(model)
    ids = symbol_ids(model, kit)
    assert len(set(ids.values())) == len(kit)
    for function, text in ids.items():
        assert text == render_id(function)
        record = functions(model)[function]
        assert text != f"{item_designation(model, record.item)}.{record.name}"


def test_missing_port_is_refused_by_name() -> None:
    """A Pick whose ports omit a port of its function raises `ProblemError` naming that port."""
    model = planted_model()
    kit = kit_for(model)
    coil = _function_named(model, "coil")
    pick = kit[coil]
    omitted = min(pick.ports)
    trimmed = dataclasses.replace(
        pick, ports=frozendict({p: n for p, n in pick.ports.items() if p != omitted})
    )
    bad = frozendict({**kit, coil: trimmed})
    with pytest.raises(ProblemError, match=re.escape(ports(model)[omitted].name)):
        pin_names(model, bad, symbol_ids(model, bad))


def test_stray_port_is_refused() -> None:
    """A Pick that names a port its function does not have raises `ProblemError`."""
    model = planted_model()
    kit = kit_for(model)
    coil = _function_named(model, "coil")
    pick = kit[coil]
    stray = next(p for p, record in ports(model).items() if record.function != coil)
    extra = dataclasses.replace(pick, ports=frozendict({**pick.ports, stray: "X"}))
    bad = frozendict({**kit, coil: extra})
    with pytest.raises(ProblemError, match="does not have"):
        pin_names(model, bad, symbol_ids(model, bad))


def test_pin_names_map_each_port_to_its_symbol_and_port_name() -> None:
    """Each port of a drawn function maps to `PinRef(symbol id, name from Pick.ports)`."""
    model = planted_model()
    kit = kit_for(model)
    ids = symbol_ids(model, kit)
    pins = pin_names(model, kit, ids)
    coil = _function_named(model, "coil")
    a1 = next(p for p, r in ports(model).items() if r.function == coil and r.name == "A1")
    assert pins[a1] == PinRef(ids[coil], "in")
    expected = {
        p: PinRef(ids[lead], n) for lead, pick in kit.items() for p, n in pick.ports.items()
    }
    assert dict(pins) == expected
