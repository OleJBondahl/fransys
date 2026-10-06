"""D5, step 6 (B2a): an end on a power net takes the net's symbol, not a reference (R5).

`with_power_ends` flags the decided ends of ports in the power table; each case below is one
ruling of D5. Ports `12` and `21` are the two ends of a severed pair; `31` and `41` join a star.
"""

from dataclasses import replace

from samples import hid

from fransys_layout.stages.references.power import with_power_ends
from fransys_layout.stages.references.types import MarkerDecision, References
from fransys_layout.stages.types import MarkerSide, PowerEnd, StubText

_SUPPLY = "power-supply"


def _end(number: int, *, symbol: str = _SUPPLY, text: str | None = "24V") -> PowerEnd:
    port = hid("port", number)
    return PowerEnd(port=port, kind="supply", symbol=symbol, text=text)


def _table(*numbers: int) -> dict:
    return {hid("port", n): _end(n) for n in numbers}


def _marker(
    port: int, partner: int, side: MarkerSide = MarkerSide.OWNER, **fields: object
) -> MarkerDecision:
    """A decided end at port `port`, naming port `partner`; `fields` are the rest."""
    return MarkerDecision(
        connection=hid("conductor", 1),
        function=hid("function", port // 10),
        port=hid("port", port),
        side=side,
        drawing_set=1,
        page=1,
        size=(40, 8),
        partner=hid("port", partner),
        partner_set=1,
        partner_page=2,
        **fields,  # ty: ignore[invalid-argument-type] -- a test passes real field values
    )


def test_both_ends_of_a_severed_pair_on_a_power_net_take_the_symbol_and_the_text() -> None:
    """(a) The pair `12`-`21` on a 24 V net: two power ends, none a reference, text `24V`."""
    # UNDO: references/power.py `_flagged`: `symbol=end.symbol` -> `symbol=""` (a reference)
    pair = (_marker(12, 21), replace(_marker(21, 12), side=MarkerSide.USER))
    found = with_power_ends(pair, _table(12, 21))
    assert [(one.port, one.symbol, one.symbol_text) for one in found] == [
        (hid("port", 12), _SUPPLY, "24V"),
        (hid("port", 21), _SUPPLY, "24V"),
    ]
    # kept in the stream, with the bookkeeping the cut and the lint still count
    assert [(one.side, one.partner, one.star) for one in found] == [
        (one.side, one.partner, one.star) for one in pair
    ]


def test_every_end_of_a_star_on_a_power_net_takes_the_symbol_and_none_a_number() -> None:
    """(b) A star of four ends (the reference and three branches): four power ends, no `#n`."""
    # UNDO: references/power.py `_takes_symbol`: `one.star != "off"` -> `one.star == ""` (a star
    #   end stays a reference)
    star = (
        _marker(12, 31, star="ref"),
        _marker(31, 12, star="branch", side=MarkerSide.USER),
        _marker(41, 12, star="branch", side=MarkerSide.USER),
        _marker(51, 12, star="branch", side=MarkerSide.USER),
    )
    found = with_power_ends(star, _table(12, 31, 41, 51))
    value = _value(found)
    assert len(value.power) == 4 == len(value.markers)
    assert {one.symbol for one in found} == {_SUPPLY}
    assert all(one.text == "" for one in found)  # nothing printed as a reference or a stub


def test_a_joined_run_decides_one_end_so_it_gets_one_symbol() -> None:
    """(c) A run of three ports wired beside each other keeps the marker of its first end only;
    the other two are wired, have none, and so get no symbol: exactly one power end."""
    # UNDO: references/power.py `_takes_symbol`: `return one.port in power and ...` -> `return
    #   False`
    run = (_marker(12, 21),)
    found = with_power_ends(run, _table(12, 21, 31))
    assert [one.port for one in _value(found).power] == [hid("port", 12)]


def test_an_off_stub_and_a_reference_merged_with_one_stay_stub_labels() -> None:
    """(d) A wire leaving the drawing keeps its stub label (LD7), merged with a reference or not."""
    # UNDO: references/power.py `_takes_symbol`: drop `and one.star != "off" and one.merge is None`
    stub = StubText(cable="-W1", far="+DB-X0", port=":1")
    off = _marker(12, 12, star="off", end_text=stub, text="-W1")
    merged = _marker(21, 31, star="ref", merge=stub)
    plain = _marker(31, 21)
    found = with_power_ends((off, merged, plain), _table(12, 21, 31))
    assert [one.symbol for one in found] == ["", "", _SUPPLY]
    assert found[:2] == (off, merged)


def test_an_end_on_no_power_port_is_the_same_decision() -> None:
    """(g) A kind `NONE` port is not in the table: the very decision comes back, a reference."""
    # UNDO: references/power.py `_takes_symbol`: `one.port in power` -> `one.port not in power`
    ordinary = _marker(61, 71)
    found = with_power_ends((ordinary, _marker(12, 21)), _table(12))
    assert found[0] is ordinary
    assert found[1].symbol == _SUPPLY


def test_an_empty_power_table_changes_nothing() -> None:
    """(e, f) No supply, or an AC one, leaves the table empty: every decision is unchanged."""
    # UNDO: references/power.py `with_power_ends`: `if _takes_symbol` -> `if True` (KeyError)
    markers = (_marker(12, 21), _marker(31, 12, star="branch"))
    assert with_power_ends(markers, {}) == markers


def test_a_protective_earth_end_prints_no_text() -> None:
    """A PE end has the earth key and an empty `symbol_text`: the power text is `None`."""
    # UNDO: references/power.py `_flagged`: `end.text or ""` -> `"PE"`
    pe = {hid("port", 12): _end(12, symbol="protective-earth", text=None)}
    (found,) = with_power_ends((_marker(12, 21),), pe)
    assert (found.symbol, found.symbol_text) == ("protective-earth", "")


def _value(markers: tuple[MarkerDecision, ...]) -> References:
    """A `References` of `markers` and nothing else."""
    return References(
        joins=(),
        decisions=(),
        markers=markers,
        off_ends=(),
        digits=(),
        echoes=(),
        connections=(),
        net_groups=(),
    )
