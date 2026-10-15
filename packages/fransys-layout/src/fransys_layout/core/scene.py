"""The scene `score` reads: placed boxes with their pins, wire polylines per net, and markers.

All lengths are in G, x grows right, y grows down. A scene holds no symbol kind: a convention
the scorer needs arrives as a field here.
"""

from dataclasses import dataclass

Point = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Pin:
    """One pin at its absolute place. Pins with the same `node` are one electrical point."""

    name: str
    x: int
    y: int
    net: str | None
    node: int | None = None
    stand: bool = False
    side: str = ""  # N, E, S or W: the way a wire leaves
    box: bool = False  # a movable-pin box pin (a PLC channel)


@dataclass(frozen=True, slots=True)
class Box:
    """One placed copy of a symbol: its body box (absolute) on `page`, with its pins."""

    id: str
    page: int
    x: int
    y: int
    w: int
    h: int
    pins: tuple[Pin, ...]
    attached: bool = False  # heads a column that hangs on a box pin
    head: bool = False  # heads a fan: a protective device feeding several legs
    strip: str | None = None  # the terminal strip it belongs to


@dataclass(frozen=True, slots=True)
class Wire:
    """One routed polyline of net `net` on `page`, vertices in order."""

    net: str
    page: int
    points: tuple[Point, ...]


@dataclass(frozen=True, slots=True)
class Marker:
    """One printed cross-reference at a pin. `cls` is `tag_pair`, `arrow_pair`, `star` or `stub`."""

    net: str
    box: str
    pin: str
    page: int
    cls: str


@dataclass(frozen=True, slots=True)
class Scene:
    """Everything `score` reads. `rails` names the nets that carry a declared supply."""

    boxes: tuple[Box, ...]
    wires: tuple[Wire, ...]
    markers: tuple[Marker, ...] = ()
    rails: frozenset[str] = frozenset()
