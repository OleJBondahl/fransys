"""EA11: every public name of the engine with its surface spelling, or why it has none.

`ROWS` maps "Class.name" (the engine class that defines the name) to a tuple of entries. One
entry is `("surface", spelling)`, `("pending", order, spelling)` or `("dropped", reason)`. A name
with several spellings has several entries: build them with the helpers below, join with `+`.
A spelling is `Class.attr` or `Class.attr(kw=)`: the class is `Design`, `Layout`, `Device`, `Fn`,
`TerminalStrip` or `Terminal`, and `(kw=)` names a keyword of that call.
"""

type Entry = tuple[str, ...]


def surface(spelling: str) -> tuple[Entry, ...]:
    """One surface entry."""
    return (("surface", spelling),)


def pending(order: str, spelling: str) -> tuple[Entry, ...]:
    """One pending entry: `order` is EA-SERIES or EA-UNITS-RUNS and lands the spelling."""
    return (("pending", order, spelling),)


def dropped(reason: str) -> tuple[Entry, ...]:
    """One dropped entry."""
    return (("dropped", reason),)


_RAILS = "rails own it (EA6)"

ROWS: dict[str, tuple[Entry, ...]] = {
    "Scope.item": surface("Design.device"),
    "Item.fn": surface("Device.__getattr__"),
    "Item.as_function": surface("Device.__getattr__"),
    "Item.__getitem__": surface("Device.__getitem__"),
    "Fn.__getitem__": surface("Fn.__getitem__"),
    "Fn.plc": surface("Fn.plc"),
    "Fn.scale": surface("Fn.scale"),
    "Scope.location": surface("Design.location"),
    "Scope.group": surface("Design.function"),
    "Scope.scope": dropped(
        "internal: keys come from function and tag, repeated circuits are functions"
    ),
    "Scope.strip": surface("Design.terminal_strip"),
    "Strip.terminal": surface("TerminalStrip.__getitem__"),
    "Terminal.inner": surface("Terminal.inner"),
    "Terminal.outer": surface("Terminal.outer"),
    "Terminal.limits": surface("Terminal.limits"),
    "Scope.bridge": surface("TerminalStrip.run(bridged=)"),
    "Scope.cable": surface("Design.cable") + surface("Design.cable(length_m=)"),
    "Cable.core": surface("Cable.core"),
    "Scope.wiring": surface("Design.wire"),
    "Wiring.__call__": surface("Design.wire(n=)"),
    "Wiring.run": surface("Design.wire"),
    "Scope.net": surface("Design.earth")
    + surface("Design.net(kind=)")
    + dropped(f"net(potential=): {_RAILS}"),
    "LinkScope.link": (
        surface("Design.device(mounted_on=)")
        + surface("Design.busbar")
        + surface("Design.rail_bond")
    ),
    "Scope.supply": surface("Design.ac_supply")
    + surface("Design.dc_supply")
    + dropped(
        "rails=: ac_supply and dc_supply write the rails, a free rails mapping is no spelling (EA6)"
    ),
    "Scope.mate": surface("Design.mate"),
    "Scope.harness": surface("Design.harness"),
    "Scope.unit": surface("Design.add"),
    "Scope.unit_id": surface("Design.add"),
    "Scope.boundary": surface("Fn.limits") + surface("Design.device(interface=)"),
    "Scope.unused": surface("Design.device(unused=)"),
    "Scope.revision": surface("Design.revision"),
    "Design.project": surface("Design.project"),
    "Design.revision": surface("Design.revision"),
    "Scope.rating": surface("Design.rating"),
    "Scope.operating": surface("Design.operating"),
    "Design.draft": surface("Design.draft"),
    "Scope.chain": surface("Layout.chain"),
    "Scope.keep_together": surface("Layout.keep_together"),
    "Scope.break_before": surface("Layout.break_before"),
    "Scope.order": surface("Layout.order"),
    "Scope.symbol": surface("Layout.symbol"),
    "Scope.draw_in": surface("Layout.draw_in"),
    "Design.sheet": surface("Layout.sheet"),
    "Design.profile": surface("Layout.profile"),
}
