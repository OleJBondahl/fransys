"""`d.location(tag, text, within=)` nests a place inside a place (author-0020)."""

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

from fransys_model.vocab import AspectNode

from ..equivalence.series_parts import pair_library  # noqa: TID252 -- importlib mode puts tests/ on no path


def _parent_label(d, label: str) -> str | None:
    nodes = {r.id: r for r in d.draft().records() if isinstance(r, AspectNode)}
    (node,) = (n for n in nodes.values() if n.label == label)
    return None if node.parent is None else nodes[node.parent].label


def test_within_sets_the_outer_place_and_without_it_the_root_stays() -> None:
    d = design(pair_library())
    d.location("HOLD", "Hold")
    d.location("BATT", "Battery bay", within="HOLD")
    assert _parent_label(d, "BATT") == "HOLD"
    assert _parent_label(d, "HOLD") is None


def test_a_missing_outer_place_raises_and_lists_the_places() -> None:
    d = design(pair_library())
    d.location("HOLD", "Hold")
    with pytest.raises(AuthorError, match=r"no place 'DECK'.*places: HOLD"):
        d.location("BATT", "Battery bay", within="DECK")


def test_a_place_a_device_made_at_the_root_is_not_moved_by_within() -> None:
    d = design(pair_library(), place="BATT")
    d.device("P1", "DEMO-CONN-2P")
    d.location("HOLD", "Hold")
    with pytest.raises(AuthorError, match="already exists elsewhere"):
        d.location("BATT", "Battery bay", within="HOLD")
