"""`d.layout.*` and the function handle: each hint writes the engine's records."""

from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

lazy from fransys_model.kernel import Draft

_NAMES = ("a", "b", "k1", "k2")


def _two(parts: Draft):
    d = design(parts)
    with d.function("A", "First") as a:
        k1 = d.device("K1", "TEST-RLY-2CO")
    with d.function("B", "Second") as b:
        k2 = d.device("K2", "TEST-RLY-2CO")
    return d, a, b, k1, k2


def _engine(parts: Draft):
    e = design(parts)._engine
    a, b = e.group("A", "First"), e.group("B", "Second")
    k1 = e.item("TEST-RLY-2CO", name="A/K1", tag="K1", group=a)
    k2 = e.item("TEST-RLY-2CO", name="B/K2", tag="K2", group=b)
    return e, a, b, k1, k2


def _hint_pair(parts: Draft, surface_call, engine_call) -> list[Any]:
    d, *s = _two(parts)
    surface_call(d.layout, SimpleNamespace(**dict(zip(_NAMES, s, strict=True))))
    e, *g = _engine(parts)
    engine_call(e, SimpleNamespace(**dict(zip(_NAMES, g, strict=True))))
    got = {(type(r).__name__, r.key): r for r in d.draft().records()}
    assert got == {(type(r).__name__, r.key): r for r in e.draft().records()}
    return list(got.values())


def test_function_yields_its_handle_and_it_works_after_the_block(parts: Draft) -> None:
    d, a, b, *_ = _two(parts)
    d.layout.order(a, b)
    assert a.key != b.key


def test_function_without_as_still_works(parts: Draft) -> None:
    d = design(parts)
    with d.function("A", "First"):
        d.device("K1", "TEST-RLY-2CO")
    assert d.draft().records()


def test_order(parts: Draft) -> None:
    _hint_pair(parts, lambda lay, h: lay.order(h.a, h.b), lambda e, h: e.order(h.a, h.b))


@pytest.mark.parametrize("keyword", ["text_height_mm", "min_text_height_mm"])
def test_the_surface_profile_refuses_the_removed_text_height_keywords(parts: Draft, keyword: str) -> None:
    """R850: the text heights left the profile; a consumer passing one gets a TypeError naming it."""
    kwargs: dict[str, Any] = {keyword: Decimal("1.8")}
    with pytest.raises(TypeError, match=keyword):
        design(parts).layout.profile(**kwargs)


def test_a_prefixed_function_name_never_reaches_a_hint(parts: Draft) -> None:
    d = design(parts)
    with pytest.raises(AuthorError), d.function("=A", "First"):
        pass
    assert not d.draft().records()


def test_the_layout_door_holds_exactly_order_and_profile_and_profile_one_keyword() -> None:
    """API-022 A1: an exact allow-list, so a deleted hint added back (chain, side, ...) fails here."""
    import inspect

    from fransys_author.surface import Layout

    names = {n for n, v in vars(Layout).items() if not n.startswith("_") and callable(v)}
    assert names == {"order", "profile"}
    assert set(inspect.signature(Layout.profile).parameters) == {"self", "hide_unused_pins"}
