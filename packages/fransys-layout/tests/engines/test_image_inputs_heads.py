"""model-0238: a coil's heading is read once per unit of the set that may draw it.

A function of a nested unit can stand on a page of an outer unit's set or of the top-level
set, where its coil's tag is longer. Layout measures the heading with the unit of the set drawn,
not with the function's own unit. Every name is invented.
"""

from types import SimpleNamespace
from typing import Any

from layout_cabinet import unit_with_release

from fransys_layout.engines.schematic.read import contact_marks
from fransys_layout.engines.schematic.read.contact_marks import image_inputs
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.vocab import Unit

_ORIGIN = Origin(file="tests/engines/test_image_inputs_heads.py", line=1, note="heads")


def _unit(name: str):
    return make_id(Unit, ("heads", name))


def test_a_nested_functions_heading_is_read_for_every_set_that_may_draw_it(monkeypatch) -> None:
    """A leaf unit's coil has one heading per set unit: none, `top`, `mid` and `leaf`."""
    # UNDO: read/contact_marks.py:image_inputs, the `for one in (None, *containing_units(...))`
    #     of `heads` -> `for one in (s.unit,)` (own unit only)
    draft = Draft()
    for name, parent in (("top", None), ("mid", "top"), ("leaf", "mid")):
        pair = unit_with_release(
            ("heads", name), name=name, parent=None if parent is None else _unit(parent)
        )
        draft.extend((pair[1], pair[0]), origin=_ORIGIN)
    model = freeze(draft)
    monkeypatch.setattr(contact_marks, "coil_heading", lambda _m, _i, unit=None: str(unit))
    coil = make_id(Unit, ("heads", "coil"))  # an id only; the model holds no such item
    spec: Any = SimpleNamespace(
        function=coil,
        item=coil,
        unit=_unit("leaf"),
        roles=SimpleNamespace(contacts_apart=True, contact=False),
        switch_group=None,
    )
    inputs: Any = SimpleNamespace(functions=(spec,), spares=(), sheet=None, profile=None)
    heads = image_inputs(model, inputs).heads
    assert set(heads) == {(coil, one) for one in (None, _unit("top"), _unit("mid"), _unit("leaf"))}
    assert len(set(heads.values())) == 4
