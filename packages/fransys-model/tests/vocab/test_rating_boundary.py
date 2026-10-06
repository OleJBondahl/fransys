"""RATINGS-1 Q5, bullet 2: a boundary rating is checked like any rating (decision model-0081).

Rails are the whole model's (`port_rails`); a boundary rating is one more rating source of the
function, named in each finding. Every model is hand-built and invented.
"""

from boundary_plant import dc_supply, sink, source, state
from plant import Plant
from rating_plant import rated

from fransys_model.kernel import Finding, key_text
from fransys_model.vocab.rating_readers import FunctionRating, function_ratings
from fransys_model.vocab.tables import boundaries, functions
from fransys_model.vocab.validators.ratings import check_ratings

_AT = "but rails '+800' and '0V' stand across it at 800 V"


def _run(plant: Plant) -> tuple[Finding, ...]:
    return check_ratings(plant.model())


def _beside(dc: str) -> Plant:
    """Units `a` (the source) and `b` (the sink) side by side, `b` stating `dc` V on its `in`."""
    plant = Plant()
    dc_supply(plant)
    unit_a, unit_b = plant.unit("a"), plant.unit("b")
    function = sink(plant, unit_b, source(plant, unit_a))
    state(plant, plant.boundary(unit_b, function, key="bb"), rated(dc=dc), tag="bb")
    return plant


def test_a_boundary_rating_is_checked_across_the_conductors_between_top_level_units() -> None:
    (finding,) = _run(_beside("600"))
    assert finding.subjects == (Plant.function_id("sink", "in"),)
    assert finding.message == (
        "function 'in' of item sink is rated 600 V DC (boundary rating of unit b), " + _AT
    )
    assert _run(_beside("1000")) == ()


def test_a_boundary_rating_is_checked_against_the_rails_a_parent_carries_to_the_child() -> None:
    def nested(dc: str) -> tuple[Finding, ...]:
        plant = Plant()
        dc_supply(plant)
        outer = plant.unit("outer")
        child = plant.unit("child", parent=outer)
        function = sink(plant, child, source(plant, outer))
        state(plant, plant.boundary(child, function, key="bb"), rated(dc=dc), tag="bb")
        return _run(plant)

    (finding,) = nested("600")
    assert "(boundary rating of unit child)" in finding.message
    assert nested("800") == ()


def _two_boundaries(first: str, second: str) -> Plant:
    plant = Plant()
    dc_supply(plant)
    unit_1, unit_2 = plant.unit("u1"), plant.unit("u2")
    function = sink(plant, None, source(plant, None))
    state(plant, plant.boundary(unit_1, function, key="b1"), rated(dc=first), tag="b1")
    state(plant, plant.boundary(unit_2, function, key="b2"), rated(dc=second), tag="b2")
    return plant


def test_a_function_that_is_the_boundary_of_two_units_is_checked_against_each() -> None:
    (one,) = _run(_two_boundaries("600", "900"))
    assert "rated 600 V DC (boundary rating of unit u1)" in one.message
    both = _run(_two_boundaries("600", "700"))
    assert len(both) == 2
    assert "rated 600 V DC (boundary rating of unit u1)" in both[0].message
    assert "rated 700 V DC (boundary rating of unit u2)" in both[1].message


def test_the_boundary_and_the_part_rating_are_two_sources_each_named_in_its_finding() -> None:
    def both(part: str, boundary: str) -> tuple[Finding, ...]:
        plant = Plant()
        dc_supply(plant)
        unit = plant.unit("b")
        function = sink(plant, unit, source(plant, None), part_rating=rated(dc=part))
        state(plant, plant.boundary(unit, function, key="bb"), rated(dc=boundary), tag="bb")
        return _run(plant)

    found = both("500", "600")
    assert [f.message.split(", but")[0] for f in found] == [
        "function 'in' of item sink is rated 500 V DC (part or template rating)",
        "function 'in' of item sink is rated 600 V DC (boundary rating of unit b)",
    ]
    (only,) = both("900", "600")
    assert "rated 600 V DC (boundary rating of unit b)" in only.message


def test_a_boundary_rating_never_falls_back_to_the_part_and_the_part_does_not_to_it() -> None:
    plant = Plant()
    dc_supply(plant)
    unit = plant.unit("b")
    function = sink(plant, unit, source(plant, None), part_rating=rated(dc="500"))
    state(plant, plant.boundary(unit, function, key="bb"), rated(ac="250"), tag="bb")
    model = plant.model()
    assert function_ratings(model, function) == (
        FunctionRating(rated(dc="500"), None),
        FunctionRating(rated(ac="250"), unit),
    )
    (finding,) = check_ratings(model)
    assert "rated 500 V DC (part or template rating)" in finding.message


def test_a_receiving_unit_that_declares_no_supply_gets_no_finding_until_a_supply_reaches_it() -> (
    None
):
    """Unit `rx` states 600 V on connector `entry`; its `motor` (500 V) hangs on the same ports."""
    plant = Plant()
    rx, tx = plant.unit("rx"), plant.unit("tx")
    entry = plant.function(plant.item("entry", unit=rx), "in")
    entry_ports = (plant.port(entry, "p0"), plant.port(entry, "p1"))
    sink(plant, rx, entry_ports, key="motor", part_rating=rated(dc="500"))
    state(plant, plant.boundary(rx, entry, key="bb"), rated(dc="600"), tag="bb")
    assert _run(plant) == ()  # no supply in the model
    dc_supply(plant)
    supplied = source(plant, tx)
    assert _run(plant) == ()  # a supply and a source, but nothing joins them to `rx`
    plant.wire(entry_ports[0], supplied[0], key="feed0")
    plant.wire(entry_ports[1], supplied[1], key="feed1")
    found = {f.subjects: f.message for f in _run(plant)}
    assert len(found) == 2
    assert "item entry is rated 600 V DC (boundary rating of unit rx)" in found[(entry,)]
    motor = Plant.function_id("motor", "in")
    assert "item motor is rated 500 V DC (part or template rating)" in found[(motor,)]


def test_without_a_boundary_facet_function_ratings_is_function_rating_as_a_tuple() -> None:
    plant = Plant()
    dc_supply(plant)
    unit = plant.unit("b")
    ports = source(plant, None)
    rated_one = sink(plant, unit, ports, key="one", part_rating=rated(dc="500"))
    bare = sink(plant, unit, ports, key="two")
    plant.boundary(unit, rated_one, key="b1")
    plant.boundary(unit, bare, key="b2")
    model = plant.model()
    assert function_ratings(model, rated_one) == (FunctionRating(rated(dc="500"), None),)
    assert function_ratings(model, bare) == ()
    unknown = Plant.function_id("nobody", "in")
    assert unknown not in functions(model)
    assert function_ratings(model, unknown) == ()


def test_the_boundary_sources_come_in_boundary_id_order() -> None:
    model = _two_boundaries("600", "700").model()
    function = Plant.function_id("sink", "in")
    order = sorted(boundaries(model).values(), key=lambda b: b.id)
    assert [r.unit for r in function_ratings(model, function)] == [b.unit for b in order]
    assert {key_text(b) for b in order} == {"b1", "b2"}
