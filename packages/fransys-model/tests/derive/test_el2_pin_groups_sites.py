"""Characterisation of the pin-group sites (EL-2 pin groups, model-0293): outputs stay as pinned.

Each derive module whose terminal or connector read became a role read is called on the planted
model of `roles_plants`, so a switch that changes a result fails here.
"""

from typing import Any

from plant import Plant
from roles_plants import roles_plant

from fransys_model.derive import connector_box_lines, schematic_functions
from fransys_model.derive.connectors import connector_items
from fransys_model.derive.designation import prints_connector_label
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.lookups import conductors_by_role
from fransys_model.derive.tag_text import is_device_terminal, tag_text
from fransys_model.kernel import SchemaError
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import functions

MODEL, IDS = roles_plant()
_NAMES = {f.id: f.name for f in functions(MODEL).values()}


def _outcome(call: Any) -> str:
    """The call's result, or the name of the `SchemaError` it raises (the plant has no numbers)."""
    try:
        return repr(call())
    except SchemaError:
        return "SchemaError"


def test_structure_draws_every_function_of_the_plant() -> None:
    """No cable and no board in the plant, so `schematic_functions` keeps every function."""
    assert sorted(_NAMES[f] for f in schematic_functions(MODEL)) == sorted(_NAMES.values())


def test_connectors_lists_none_without_a_connector_facet() -> None:
    """The planted connector has no template, so `connector_items` finds no connector item."""
    assert connector_items(MODEL) == ()


def test_designation_prints_a_label_only_for_the_connector() -> None:
    """`prints_connector_label` is true for the planted connector, false for other kinds."""
    printed = {
        n
        for n in ("coil", "terminal_1", "connector", "no")
        if prints_connector_label(MODEL, IDS[n])
    }
    assert printed == {"connector"}


def test_tag_text_and_box_lines_need_a_numbered_plant() -> None:
    """The plant carries no designation, so each text function refuses the same way."""
    for name in ("coil", "terminal_1", "connector"):
        assert _outcome(lambda n=name: tag_text(MODEL, IDS[n])) == "SchemaError"
        assert _outcome(lambda n=name: connector_box_lines(MODEL, IDS[n])) == "SchemaError"


def test_a_terminal_function_of_a_non_terminal_item_is_a_device_terminal() -> None:
    """`is_device_terminal`: true only for a terminal-kind function without a terminal facet."""
    plant = Plant()
    device = plant.function(plant.item("device"), "a2", kind=FunctionKind.TERMINAL)
    other = plant.function(plant.item("other"), "coil", kind=FunctionKind.COIL)
    model = plant.model()
    assert is_device_terminal(model, device)
    assert not is_device_terminal(model, other)
    assert not is_device_terminal(MODEL, IDS["terminal_1"])


def test_conductors_by_role_of_an_unwired_terminal_is_empty() -> None:
    """The planted terminals have no conductor landed, so no role has one."""
    assert conductors_by_role(MODEL, build_indexes(MODEL), IDS["item:terminal_1"]) == {}
