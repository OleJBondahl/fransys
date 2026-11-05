"""The ids of the page Drawing elements: the ids the retired `layout.drawn_*` records had (R234).

A Drawing no longer orders its elements by these ids (they follow the instance path); the ids
stay stable while no record of those kinds exists. The stand-ins are no record: they hold
only the kind text the id is derived from.
"""

from fransys_model.kernel import make_id, render_id

__all__ = ["core_symbol_id", "lead_id", "outline_id", "symbol_id", "wire_id"]

_KEY = ("layout", "core")


def _id(kind: str, key: tuple[str, ...]) -> str:
    return render_id(make_id(type("Kind", (), {"__kind__": kind}), key))


def symbol_id(*key: str) -> str:
    """The render id of the symbol under `key`."""
    return _id("layout.drawn_symbol", key)


def core_symbol_id(sym: str) -> str:
    """The render id of the drawn symbol of core symbol `sym`."""
    return symbol_id(*_KEY, "drawn_symbol", sym)


def wire_id(number: int, net: str, index: int) -> str:
    """The render id of core wire `index` of drawing set `number`, on `net`."""
    return lead_id(*_KEY, "drawn_wire", str(number), net, str(index))


def outline_id(unit: str, page: int, run: int) -> str:
    """The render id of frame number `run` of `unit` on core page `page`."""
    return _id("layout.drawn_outline", (*_KEY, "drawn_outline", unit, str(page), str(run)))


def lead_id(*key: str) -> str:
    """The render id of the wire under `key`: a lead no core wire holds, such as a power lead."""
    return _id("layout.drawn_wire", key)
