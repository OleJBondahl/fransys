"""`terminal_items` is built once per model digest (decision model-0084)."""

from examples import core_model

from fransys_model.derive import lookups
from fransys_model.derive.lookups import terminal_items
from fransys_model.kernel import Model, Origin, evolve, make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.facets import TerminalFacet

_ORIGIN = Origin(file="test_terminal_items_cache.py", line=1, note="fixture")
_ONE = make_id(Item, ("plant", "strip", "t1"))
_TWO = make_id(Item, ("plant", "strip", "t2"))


def _terminal(key: str, index: int) -> tuple[Item, TerminalFacet]:
    item = Item(
        id=make_id(Item, ("plant", "strip", key)),
        key=("plant", "strip", key),
        part=None,
        parent=None,
        position=None,
        tag=None,
        description="Invented",
    )
    facet = TerminalFacet(
        id=make_id(TerminalFacet, ("plant", "strip", key, "facet")),
        key=("plant", "strip", key, "facet"),
        subject=item.id,
        group="L1",
        index=index,
    )
    return item, facet


def _model(*keys: str) -> Model:
    records = [record for number, key in enumerate(keys, 1) for record in _terminal(key, number)]
    return evolve(core_model(), put=records, origin=_ORIGIN)


def test_many_calls_on_one_digest_build_once_and_a_second_digest_builds_its_own() -> None:
    """Equal digests share one build; the answer is the set of items with a terminal facet."""
    lookups.terminal_items.cache_clear()
    one = _model("t1")
    same = _model("t1")
    two = _model("t1", "t2")
    assert one is not same
    assert one.digest == same.digest != two.digest
    for _ in range(5):
        assert terminal_items(one) == frozenset({_ONE})
        assert terminal_items(same) == frozenset({_ONE})
    assert lookups.terminal_items.builds == 1
    assert terminal_items(two) == frozenset({_ONE, _TWO})
    assert lookups.terminal_items.builds == 2
    assert terminal_items(core_model()) == frozenset()
    assert lookups.terminal_items.builds == 3
