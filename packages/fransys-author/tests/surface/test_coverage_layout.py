"""EA11 `d.layout.*` and the function handle: each hint writes the engine's records."""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

from fransys_model.layout import SymbolChoice
from fransys_model.vocab import FunctionKind
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


def _hint_pair(parts: Draft, surface_call, engine_call) -> list:
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


def test_keep_together_and_break_before(parts: Draft) -> None:
    _hint_pair(
        parts,
        lambda lay, h: (lay.keep_together(h.a, h.b), lay.break_before(h.b)),
        lambda e, h: (e.keep_together(h.a, h.b), e.break_before(h.b)),
    )


def test_chain_takes_a_function_a_device_and_a_terminal(parts: Draft) -> None:
    d = design(parts)
    k1 = d.device("K1", "TEST-RLY-2CO")
    k2 = d.device("K2", "TEST-RLY-2CO")
    t = d._engine.strip("X1").terminal("TEST-TB")
    d.layout.chain(k1.coil, k2.coil, t)
    e = design(parts)._engine
    i1 = e.item("TEST-RLY-2CO", name="K1", tag="K1")
    i2 = e.item("TEST-RLY-2CO", name="K2", tag="K2")
    e.chain(i1.fn("coil"), i2.fn("coil"), e.strip("X1").terminal("TEST-TB"))
    assert d.draft().records() == e.draft().records()


def test_symbol_for_a_kind_and_for_a_function(parts: Draft) -> None:
    _hint_pair(
        parts,
        lambda lay, h: (
            lay.symbol(FunctionKind.COIL, "coil_sym"),
            lay.symbol(h.k1.coil, "coil_sym", {"A1": "1"}),
        ),
        lambda e, h: (
            e.symbol(FunctionKind.COIL, "coil_sym"),
            e.symbol(h.k1.fn("coil"), "coil_sym", {"A1": "1"}),
        ),
    )


def test_symbol_for_a_device_is_one_choice_per_function(parts: Draft) -> None:
    got = _hint_pair(
        parts,
        lambda lay, h: lay.symbol(h.k1, "sym"),
        lambda e, h: e.symbol(h.k1, "sym"),
    )
    assert len([r for r in got if isinstance(r, SymbolChoice)]) == 3


def test_a_string_kind_raises(parts: Draft) -> None:
    d, *_ = _two(parts)
    with pytest.raises(AuthorError, match=r"a kind is a name: FunctionKind\.X"):
        d.layout.symbol("coil", "coil_sym")


def test_draw_in(parts: Draft) -> None:
    _hint_pair(
        parts,
        lambda lay, h: lay.draw_in(h.k1.coil, h.b),
        lambda e, h: e.draw_in(h.k1.fn("coil"), h.b),
    )


_SHEET = {
    "width_mm": 420,
    "height_mm": 297,
    "content_x_mm": 10,
    "content_y_mm": 10,
    "content_width_mm": 400,
    "content_height_mm": 277,
    "frame_columns": 8,
    "frame_rows": 6,
    "module_mm": Decimal("2.5"),
}


def test_sheet_then_profile(parts: Draft) -> None:
    d = design(parts)
    e = design(parts)._engine
    d.layout.profile(sheet=d.layout.sheet("A3", **_SHEET))
    e.profile(sheet=e.sheet("A3", **_SHEET))
    assert d.draft().records() == e.draft().records()


def test_a_prefixed_function_name_never_reaches_a_hint(parts: Draft) -> None:
    d = design(parts)
    with pytest.raises(AuthorError), d.function("=A", "First"):
        pass
    assert not d.draft().records()


def test_a_bad_function_argument_raises_naming_the_type(parts: Draft) -> None:
    d, *_ = _two(parts)
    with pytest.raises(AuthorError, match="int"):
        d.layout.chain(3)
