"""layout-0094: an end on a power net takes the net's symbol, not a reference.

`with_power_ends` flags the decided ends of ports in the power table; each case below is one
ruling of layout-0094. Ports `12` and `21` are the two ends of a severed pair; `31` and `41` join
a star.
"""

from dataclasses import replace

from samples import hid

from fransys_layout.stages.references.power import with_power_ends
from fransys_layout.stages.references.types import MarkerDecision, References
from fransys_layout.stages.types import MarkerSide, PowerEnd

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


def test_a_joined_run_decides_one_end_so_it_gets_one_symbol() -> None:
    """(c) A run of three ports wired beside each other keeps the marker of its first end only;
    the other two are wired, have none, and so get no symbol: exactly one power end."""
    # UNDO: references/power.py `_takes_symbol`: `return one.port in power and ...` -> `return
    #   False`
    run = (_marker(12, 21),)
    found = with_power_ends(run, _table(12, 21, 31))
    assert [one.port for one in _value(found).power] == [hid("port", 12)]


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
