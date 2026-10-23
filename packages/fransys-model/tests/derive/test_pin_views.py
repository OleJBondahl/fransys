"""`connector_pin_views` and `connector_pin_mates`: connector pins drawn as views, and mates."""

from plant import Plant

from fransys_model.derive import connector_pin_mates, connector_pin_views, template_gender
from fransys_model.vocab.enums import FunctionKind


def _connector(plant: Plant, item: str, *names: str, unit=None):
    """Item `item` with one connector function `c` holding ports `names`."""
    item_id = plant.item(item, unit=unit)
    function = plant.function(item_id, "c", kind=FunctionKind.CONNECTOR)
    return item_id, function, [plant.port(function, name) for name in names]


def test_each_port_of_a_connector_is_one_row_and_a_contact_has_none() -> None:
    plant = Plant()
    _, _, (p1, p2) = _connector(plant, "J1", "1", "2")
    plant.pin("K1", "aux", "13")
    rows = connector_pin_views(plant.model(), frozenset(), frozenset())
    assert [row.port for row in rows] == sorted([p1, p2])
    assert [row.name for row in sorted(rows, key=lambda r: r.port)] == [
        name for _, name in sorted([(p1, "1"), (p2, "2")])
    ]
    assert all(row.gender == "" and row.mate is None for row in rows)


def test_a_connector_of_a_chained_item_has_no_row() -> None:
    plant = Plant()
    item, _, _ = _connector(plant, "J1", "1")
    assert connector_pin_views(plant.model(), frozenset({item}), frozenset()) == ()


def test_a_pin_is_drawn_when_wired_or_its_mate_is() -> None:
    plant = Plant()
    _, f1, (a1, a2) = _connector(plant, "J1", "1", "2")
    _, f2, (b1, b2) = _connector(plant, "J2", "1", "2")
    plant.mate(f1, f2)
    rows = {r.port: r for r in connector_pin_views(plant.model(), frozenset(), frozenset({a1}))}
    assert {port for port, row in rows.items() if row.drawn} == {a1, b1}
    assert rows[a1].mate == b1
    assert rows[a2].mate == b2
    assert not any(row.elsewhere for row in rows.values())


def test_a_boundary_pin_no_wire_inside_reaches_is_kept_elsewhere() -> None:
    plant = Plant()
    unit = plant.unit("u")
    _, function, (a1, a2) = _connector(plant, "J1", "1", "2", unit=unit)
    plant.boundary(unit, function)
    rows = {r.port: r for r in connector_pin_views(plant.model(), frozenset(), frozenset())}
    assert all(row.drawn and row.elsewhere for row in rows.values())
    plant.wire(a1, plant.pin("K1", "aux", "13"), key="w")
    rows = {r.port: r for r in connector_pin_views(plant.model(), frozenset(), frozenset({a1}))}
    assert rows[a1].drawn
    assert not rows[a1].elsewhere
    assert not rows[a2].drawn


def test_an_unused_boundary_function_is_no_boundary_pin() -> None:
    plant = Plant()
    unit = plant.unit("u")
    _, function, _ = _connector(plant, "J1", "1", unit=unit)
    plant.boundary(unit, function)
    plant.unused(function)
    (row,) = connector_pin_views(plant.model(), frozenset(), frozenset())
    assert not row.drawn


def test_mated_pins_pair_by_name_with_the_later_key_lower() -> None:
    plant = Plant()
    _, f1, (a1, a2) = _connector(plant, "J1", "1", "2")
    _, f2, (b1, _) = _connector(plant, "J2", "1", "3")
    plant.mate(f1, f2)
    pairs = connector_pin_mates(plant.model(), frozenset({a1, a2, b1}))
    assert [(p.upper, p.lower) for p in pairs] == [(a1, b1)]
    assert connector_pin_mates(plant.model(), frozenset({a1, a2})) == ()


def test_a_template_without_a_connector_facet_has_no_gender() -> None:
    assert template_gender(Plant().model(), None) is None
