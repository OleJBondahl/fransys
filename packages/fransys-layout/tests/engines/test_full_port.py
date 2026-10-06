"""F9 (layout deep dive, D10, amended): an off-stub's far end reads its product designation,
the shortest text that names the device: a location segment and the item, no `=` function
segment, then the port suffix. `end_text` puts `stub_far_end`'s head and tail in the stub's
`StubText` as they come (A3).

Can-fail, checked by hand on the old `full_port` (a join of `stub_far_end`'s pair, folded into
`end_text` by A3): with its head read from `reference_designation` again the result carried the
"=" function segment and the test failed. Not re-run since the head is `stub_far_end`'s alone.
"""

from layout_cabinet import build_cabinet

from fransys_model.derive.drawing_text import stub_far_end
from fransys_model.kernel import freeze
from fransys_model.vocab.tables import functions, items, ports


def _far_end_of(tag: str, pin: str) -> tuple[str, str]:
    model = freeze(build_cabinet())
    (item,) = (i for i in items(model).values() if i.key == ("cabinet", tag))
    (port,) = (
        p.id
        for p in ports(model).values()
        if functions(model)[p.function].item == item.id and p.name == pin
    )
    return stub_far_end(model, port)


def test_the_far_end_of_an_off_stub_is_named_by_its_product_designation() -> None:
    """Contactor `K1`, placed at `+C1` in a function group, reads head "+C1-K1" and tail ":1",
    with the location, the item and the port suffix, and no "=" segment."""
    head, tail = _far_end_of("k1", "1")
    assert (head, tail) == ("+C1-K1", ":1")
    assert "=" not in head
