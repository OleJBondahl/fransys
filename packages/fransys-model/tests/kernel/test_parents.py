"""`parent_chain`: the one leaf-to-root walk over a parent relation (REVIEW-M M6).

Plain strings stand for nodes and a dict for the parent relation. Each walk is read through
`islice`, so a broken walk that never ends fails the assertion instead of hanging the run.
"""

from itertools import islice

from fransys_model.kernel import parent_chain

_BOUND = 20


def _walk(parents: dict[str, str | None], start: str | None) -> list[str]:
    """The chain from `start`, at most `_BOUND` nodes: a longer one is a walk that never ends."""
    return list(islice(parent_chain(parents.get, start), _BOUND))


def test_a_chain_runs_from_the_leaf_to_the_root() -> None:
    assert _walk({"leaf": "mid", "mid": "root", "root": None}, "leaf") == ["leaf", "mid", "root"]


def test_a_root_is_a_chain_of_itself() -> None:
    assert _walk({"root": None}, "root") == ["root"]


def test_a_start_of_none_yields_nothing() -> None:
    assert _walk({"a": None}, None) == []


def test_a_two_node_cycle_ends_before_the_first_node_repeats() -> None:
    assert _walk({"a": "b", "b": "a"}, "a") == ["a", "b"]


def test_a_self_cycle_yields_the_node_once() -> None:
    assert _walk({"a": "a"}, "a") == ["a"]


def test_a_tail_into_a_cycle_yields_each_node_once() -> None:
    parents: dict[str, str | None] = {"leaf": "a", "a": "b", "b": "c", "c": "a"}
    assert _walk(parents, "leaf") == ["leaf", "a", "b", "c"]


def test_a_start_the_relation_does_not_know_is_yielded_and_parent_of_decides() -> None:
    """`dict.get` says `None` for it, so the chain is the start alone."""
    assert _walk({"a": None}, "unknown") == ["unknown"]


def test_the_walk_is_lazy_and_never_asks_beyond_where_the_caller_stopped() -> None:
    asked: list[str] = []

    def parent_of(node: str) -> str | None:
        asked.append(node)
        return {"a": "b", "b": "c", "c": None}[node]

    chain = parent_chain(parent_of, "a")
    assert next(chain) == "a"
    assert asked == []
    assert next(chain) == "b"
    assert asked == ["a"]
