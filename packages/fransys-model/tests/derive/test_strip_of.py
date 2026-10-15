"""Tests: `strip_of` is a terminal's parent item, and `strip_set` is the set of those parents."""

from plant import Plant

from fransys_model.derive.facts.strips import strip_of
from fransys_model.derive.lookups import strip_set
from fransys_model.kernel import Id, make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.terminals import terminal_items


def _terminal(plant: Plant, strip: Id[Item] | None, name: str, group: str, index: int) -> Id[Item]:
    """A terminal item under `strip` (`None`: a root), with its `terminal` facet."""
    terminal = plant.item(name, parent=strip, part=plant.part("X"))
    key = (name, "terminal")
    plant.add(
        TerminalFacet(
            id=make_id(TerminalFacet, key),
            key=key,
            subject=terminal,
            group=group,
            index=index,
        )
    )
    return terminal


def test_both_groups_of_a_strip_read_the_one_strip() -> None:
    """A strip X1 with terminals in two groups: each terminal reads X1 as its strip."""
    plant = Plant()
    strip = plant.item("X1", designation="X1")
    group_a = [_terminal(plant, strip, f"x1-a{n}", "A", n) for n in (1, 2)]
    group_b = [_terminal(plant, strip, "x1-b1", "B", 1)]
    model = plant.model()
    assert len(terminal_items(model)) == 3
    assert [strip_of(model, t) for t in group_a + group_b] == [strip, strip, strip]
    assert strip_set(model) == frozenset({make_id(Item, ("X1",))})


def test_a_terminal_under_a_part_less_parent_reads_that_parent() -> None:
    """A terminal under a bridge item with no part: the bridge is still its strip."""
    plant = Plant()
    bridge = plant.item("bridge", designation="BR1")
    terminal = _terminal(plant, bridge, "bridge-t1", "", 1)
    model = plant.model()
    assert len(terminal_items(model)) == 1
    assert strip_of(model, terminal) == make_id(Item, ("bridge",))
    assert strip_set(model) == frozenset({make_id(Item, ("bridge",))})


def test_a_non_terminal_and_a_root_terminal_have_no_strip() -> None:
    """A coil under a strip is not a terminal, and a terminal with no parent has no strip."""
    plant = Plant()
    strip = plant.item("X1", designation="X1")
    coil = plant.item("coil", parent=strip, part=plant.part("K"), designation="K1")
    root_terminal = _terminal(plant, None, "root-t", "", 1)
    model = plant.model()
    assert strip_of(model, coil) is None
    assert strip_of(model, root_terminal) is None
    assert strip_of(model, make_id(Item, ("missing",))) is None
