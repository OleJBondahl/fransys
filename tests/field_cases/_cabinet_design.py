"""The cabinet design two stub field cases share: a unit whose valve cables each leave toward one device."""

from typing import Any, NamedTuple

import fransys as fr

_VALVE = (("coil", "A1"), ("coil", "A2"), ("co_1", "11"), ("co_1", "14"))


class _Cabinet(NamedTuple):
    F8: Any
    K: tuple[Any, ...]
    DI: Any
    XF: Any


class _Top(NamedTuple):
    T: Any


def cabinet_design(cables: int) -> fr.Design:
    """A cabinet unit CSC whose `cables` valve cables each leave from a breaker, a relay, an input and a terminal toward one device."""

    @fr.unit("demo-inner", revision=1, interface_version=1, date="2026-01-01", text="r", by="XX")
    def inner(d: fr.Design) -> _Cabinet:
        d.layout.profile(hide_unused_pins=True)
        relays = tuple(d.device(f"K{k}", "DEMO-RLY-4CO-24", interface=("co_1",)) for k in range(1, 2 * cables, 2))
        f8 = d.device("F8", "DEMO-MCB-2P", interface=("pole_1",))
        xf = d.terminal_strip("XF", "DEMO-TB-2.5", cables + 3, interface=tuple(range(4, cables + 4)), bridged=True)
        d.series(f8.pole_1["1"], xf[1], wire=("BK", 1.5))
        di = d.device("DI", "DEMO-PLC-DI-16", interface=tuple(f"di_{9 + 2 * n}" for n in range(cables)))
        return _Cabinet(f8, relays, di, xf)

    @fr.unit("demo-outer", revision=1, interface_version=1, date="2026-01-01", text="r", by="XX")
    def outer(d: fr.Design) -> _Top:
        d.layout.profile(hide_unused_pins=True)
        cab = d.add(inner, "CSC")
        for n in range(cables):
            pins = (cab.F8.pole_1["2"], cab.K[n].co_1["14"], getattr(cab.DI, f"di_{9 + 2 * n}")[str(9 + 2 * n)], cab.XF[4 + n])
            with d.function(f"CV{n + 1}", f"Valve {n + 1}"):
                valve = d.device(f"M{n + 1}", "DEMO-RLY-4CO-24")
                cable = d.cable(f"W{n + 1:04d}", "DEMO-CBL-4G1.5")
                for core, (pin, (name, port)) in enumerate(zip(pins, _VALVE, strict=True), start=1):
                    cable.core(core, pin, getattr(valve, name)[port])
        return _Top(d.device("T", "DEMO-RLY-4CO-24"))

    d = fr.design("demo_parts")
    d.add(outer, "U1")
    return d
