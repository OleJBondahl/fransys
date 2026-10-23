"""`ink_net`: a declared net's pins are one ink net, with or without a conductor."""

from plant import Plant

from fransys_model.derive import ink_net as _ink_net


def ink_net(model, port):
    """`_ink_net`, which is never `None` for a port of the model."""
    found = _ink_net(model, port)
    assert found is not None
    return found


def _pins(plant: Plant, *names: str) -> list:
    return [plant.port(plant.function(plant.item(n), "fn"), "1") for n in names]


def test_a_net_without_a_conductor_is_one_ink_net() -> None:
    """Two pins joined by a declared net alone read as one net, not a singleton each."""
    plant = Plant()
    a, b, c = _pins(plant, "a", "b", "c")
    plant.net("sig", (a, b))
    model = plant.model()
    assert ink_net(model, a) == ink_net(model, b)
    assert set(ink_net(model, a).ports) == {a, b}
    assert ink_net(model, c).ports == (c,)


def test_a_conductor_realised_net_is_unchanged() -> None:
    """A declared net the conductors already realise keeps its physical net."""
    plant = Plant()
    a, b, c = _pins(plant, "a", "b", "c")
    plant.wire(a, b, key="w1")
    plant.wire(b, c, key="w2")
    plant.net("sig", (a, b, c))
    model = plant.model()
    assert set(ink_net(model, a).ports) == {a, b, c}
    assert ink_net(model, a) == ink_net(model, c)


def test_a_single_pin_net_is_unchanged() -> None:
    """A declared net of one pin joins nothing."""
    plant = Plant()
    a, b = _pins(plant, "a", "b")
    plant.net("solo", (a,))
    model = plant.model()
    assert ink_net(model, a).ports == (a,)
    assert ink_net(model, a) != ink_net(model, b)
