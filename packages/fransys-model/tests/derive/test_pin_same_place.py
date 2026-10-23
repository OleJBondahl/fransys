"""`same_place`: one answer to whether a stored pin still sits where it was (EL-9 G, DES-20)."""

from fransys_model.derive.numbering_moves import designation_moves, gone_or_moved, same_place
from fransys_model.derive.rows_baseline import NumberingItem, NumberingPins
from fransys_model.derive.rows_numbering import PinPosition

_KEY = ("k1",)


def _pin(scope: tuple[str, ...] | None, code: str | None) -> NumberingItem:
    return NumberingItem(key=_KEY, scope=scope, code=code, text="K1", authored=False)


def _source(pin: NumberingItem) -> NumberingPins:
    return NumberingPins(items=(pin,), retired=())


def test_a_pin_is_in_place_while_scope_and_code_match() -> None:
    """Same scope and code is in place; a changed scope or a changed code is not."""
    pin = _pin(("a",), "K")
    assert same_place(pin, PinPosition(key=_KEY, scope=("a",), code="K"))
    assert not same_place(pin, PinPosition(key=_KEY, scope=("b",), code="K"))
    assert not same_place(pin, PinPosition(key=_KEY, scope=("a",), code="Q"))


def test_gone_or_moved_and_designation_moves_use_the_same_answer() -> None:
    """A moved pin is retired and never listed as a text move; an in-place one is the reverse."""
    pin = _pin(("a",), "K")
    moved = PinPosition(key=_KEY, scope=("b",), code="K")
    kept = PinPosition(key=_KEY, scope=("a",), code="K")
    assert [r.text for r in gone_or_moved(_source(pin), [moved])] == ["K1"]
    assert gone_or_moved(_source(pin), [kept]) == ()
    current = NumberingPins(
        items=(NumberingItem(key=_KEY, scope=("b",), code="K", text="K2", authored=False),),
        retired=(),
    )
    assert designation_moves(_source(pin), current) == ()
