"""Field case: a strip terminal wired to relays that stand on two pages of one bank.
The bug (KI-647, WIRE-29): the terminal is drawn once and the far page carries stubs; no producer plans a terminal copy per page.
Fix decision: TERMINAL-PAGE-COPY, a producer in cut_ledger.copies plans the per-page terminal symbol."""

import itertools
from typing import NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document

_RELAYS = 36  # the bank spans two pages on the default A3 sheet (30 stay on one)


class _Io(NamedTuple):
    feed: fr.TerminalStrip


@fr.unit("demo-two-pages", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _bank(u: fr.Design) -> _Io:
    feed = u.terminal_strip("X1", "DEMO-TB-2.5-TWIN", 1, interface=True)
    with u.function("R", "Relays"):
        relays = [u.device(f"K{i + 1}", "DEMO-RLY-2CO-24") for i in range(_RELAYS)]
    zero = u.terminal_strip("X2", "DEMO-TB-2.5", _RELAYS).run("0V", _RELAYS, bridged=True)
    u.series(feed[1].inner, relays[0].coil["A1"], wire=("WH", 0.75))
    u.series(feed[1].outer, relays[-1].coil["A1"], wire=("WH", 0.75))
    for a, b in itertools.pairwise(relays):
        u.series(a.coil["A1"], b.coil["A1"], wire=("WH", 0.75))
    for n, relay in enumerate(relays, 1):
        u.series(relay.coil["A2"], zero[n].inner, wire=("BU", 0.75))
    return _Io(feed)


def test_a_terminal_wired_to_relays_on_two_pages_is_drawn_on_each() -> None:
    """The bank spans two pages and X1:1 feeds a relay on each: its terminal symbol stands on both."""
    d = fr.design("demo_parts")
    d.add(_bank, "U1")
    pages = drawn_pages(fr.build(d, unit_document("demo-two-pages")).model).values()
    on_pages = [{s.ports for s in page.symbols if s.key == "terminal"} for page in pages]
    assert len(on_pages) == 2
    assert on_pages[0] & on_pages[1], "no terminal symbol stands on both pages"
