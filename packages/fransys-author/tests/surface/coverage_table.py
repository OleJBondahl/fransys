"""Every public name of the engine with its surface spelling, or why it has none.

`ROWS` maps "Class.name" (the engine class that defines the name) to a tuple of entries. One
entry is `("surface", spelling)`, `("pending", order, spelling)` or `("dropped", reason)`. A name
"""

type Entry = tuple[str, ...]


def surface(spelling: str) -> tuple[Entry, ...]:
    """One surface entry."""
    return (("surface", spelling),)


def pending(order: str, spelling: str) -> tuple[Entry, ...]:
    """One pending entry: `order` names the pending work that lands the spelling."""
    return (("pending", order, spelling),)


def dropped(reason: str) -> tuple[Entry, ...]:
    """One dropped entry."""
    return (("dropped", reason),)


_RAILS = "rails own it (EA6)"

ROWS: dict[str, tuple[Entry, ...]] = {
    "BuildScope.item": surface("Design.device"),
    "Item.fn": surface("Device.__getattr__"),
    "Item.as_function": surface("Device.__getattr__"),
    "Item.__getitem__": surface("Device.__getitem__"),
    "Fn.__getitem__": surface("Fn.__getitem__"),
    "Fn.plc": surface("Fn.plc"),
    "Fn.scale": surface("Fn.scale"),
    "UnitScope.location": surface("Design.location"),
    "UnitScope.group": surface("Design.function"),
    "Scope.scope": dropped("internal: keys come from function and tag, repeated circuits are functions"),
    "BuildScope.strip": surface("Design.terminal_strip"),
    "Strip.terminal": surface("TerminalStrip.__getitem__"),
    "Terminal.inner": surface("Terminal.inner"),
    "Terminal.outer": surface("Terminal.outer"),
    "BuildScope.bridge": surface("TerminalStrip.run(bridged=)"),
    "BuildScope.rail": surface("TerminalStrip.run(rail=)"),
    "BuildScope.cable": surface("Design.cable") + surface("Design.cable(length_m=)"),
    "Cable.core": surface("Cable.core"),
    "Cable.open_core": surface("Cable.spare"),
    "BuildScope.wiring": surface("Design.series"),
    "Wiring.__call__": surface("Design.series"),
    "Wiring.run": surface("Design.series"),
    "BuildScope.earth": surface("Design.earth"),
    "BuildScope.net": dropped("net(kind=): d.detail.net is removed (R1493), a signal is a series or a wire") + dropped(f"net(potential=): {_RAILS}"),
    "LinkScope.link": (surface("Design.device(mounted_on=)") + surface("Design.device(joins=)") + surface("Detail.busbar")),
    "SupplyScope.supply": surface("Design.ac_supply")
    + surface("Design.dc_supply")
    + dropped("rails=: ac_supply and dc_supply write the rails, a free rails mapping is no spelling (EA6)"),
    "BuildScope.mate": surface("Design.mate"),
    "BuildScope.pole_group": surface("Design.poles"),
    "BuildScope.harness": surface("Design.harness"),
    "LinkScope.harness_item": surface("Design.harness"),
    "Scope.unit": surface("Design.add"),
    "UnitScope.unit_id": surface("Design.add"),
    "UnitScope.boundary": surface("Design.device(interface=)"),
    "UnitScope.unused": surface("Design.device(unused=)"),
    "UnitScope.unused_port": surface("Design.unused"),
    "UnitScope.boundary_if_returned": surface("Design.device(unused=)"),
    "UnitScope.revision": surface("Design.revision"),
    "Design.project": surface("Design.project"),
    "Design.revision": surface("Design.revision"),
    "UnitScope.operating": dropped("internal: a supply reads its template's envelope; no surface call (API-022)"),
    "Design.draft": surface("Design.draft"),
    "Scope.order": surface("Layout.order"),
    "UnitScope.profile": surface("Layout.profile"),
}
