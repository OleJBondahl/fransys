"""`mate_partners`: the one home of the functions across a mate (BLOCK-DIAGRAMS BD2)."""

from connector_builders import make_connector
from plant import Plant

from fransys_model.derive.mate_rows import mate_partners


def test_each_end_of_a_mate_lists_the_other_and_a_second_mate_adds_a_partner_in_id_order() -> None:
    """Both ends are keys; a connector with two mates lists both, smallest id first."""
    plant = Plant()
    for name in ("a", "b", "c"):
        plant.item(name, designation=name.upper())
    fa, _ = make_connector(plant, ("a", "J1"), ("1",))
    fb, _ = make_connector(plant, ("b", "J1"), ("1",))
    fc, _ = make_connector(plant, ("c", "J1"), ("1",))
    plant.mate(fa, fb)
    plant.mate(fa, fc, key="mate-2")
    partners = mate_partners(plant.model())
    assert partners[fa] == tuple(sorted((fb, fc)))
    assert partners[fb] == (fa,)
    assert partners[fc] == (fa,)


def test_a_model_without_mates_has_no_partners() -> None:
    """An unmated model gives an empty map."""
    assert mate_partners(Plant().model()) == {}
