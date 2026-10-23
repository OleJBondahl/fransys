"""A series' protective core: who carried it, and the earthing of a landing end (author-0044)."""

from typing import TYPE_CHECKING

from fransys_author._earth_net import earth_net
from fransys_author._keys import scoped
from fransys_author._origin import caller_origin
from fransys_author.errors import AuthorError
from fransys_author.surface._ends import Parallel

if TYPE_CHECKING:
    from fransys_author.handles import Port
    from fransys_author.surface.design import Design


def element_name(element: object) -> str:
    """The label a series element prints in a message: its tag, name or label."""
    if isinstance(element, Parallel):
        return "(" + " | ".join(element_name(member) for member in element._members) + ")"
    for attr in ("_label", "_tag", "_name"):
        text = getattr(element, attr, None)
        if text:
            return str(text)
    return type(element).__name__


def series_name(elements: tuple[object, ...]) -> str:
    """The call as the engineer wrote it, `d.series(400V, Q0, W1, M1)`, for a message."""
    return f"d.series({', '.join(element_name(element) for element in elements)})"


def refuse_carried(design: Design | None, ports: tuple[Port, ...]) -> None:
    """Raise when a port already took a series' protective core, naming that series."""
    carried = {} if design is None else design._carried
    for port in ports:
        if port.id in carried:
            label, series = carried[port.id]
            msg = f"{label} already has the protective core that {series} landed on it"
            raise AuthorError(msg)


def earth_pin(design: Design, port: Port) -> None:
    """Join `port` to the `PE` net alone, as `d.earth` does (PE-BAR B0); one net per pin."""
    net = earth_net(scoped(port.key, "pe"), (port.id,))
    design._engine._design._add(net, caller_origin())
