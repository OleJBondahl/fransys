"""`d.detail`: the calls for a case no core call writes (author-0042, API-CLARITY C2)."""

from typing import TYPE_CHECKING, NoReturn

from fransys_author.surface._removed import refuse
from fransys_author.surface._wire import _port
lazy from fransys_author.handles import Port, Terminal

if TYPE_CHECKING:
    from fransys_author.surface.design import Design


class Detail:
    """The detail calls of one design: `busbar`.

    Each is for a case no core call writes; try `d.series` first.
    Does not pair poles or take the next free terminal, as `d.series` does.
    """

    def __init__(self, design: "Design") -> None:  # noqa: UP037 -- Design imports this module: unquoted, inspect.signature raises NameError [decisions 0111, 0414]
        """Hold the surface `Design`; `d.detail` makes these."""
        self._design = design

    def busbar(self, a: Port | Terminal, b: Port | Terminal) -> None:
        """Join two pins by a busbar: a conductor of kind `bus`.

        Does not make a wire; the same pin twice raises.
        """
        design = self._design
        design._engine.link(_port(design, a), _port(design, b), kind="bus")

    if not TYPE_CHECKING:

        def __getattr__(self, name: str) -> NoReturn:
            refuse("Detail", name)


class Details:
    """The `detail` property of the surface `Design`, and the lookup of a name removed from it."""

    if not TYPE_CHECKING:

        def __getattr__(self, name: str) -> NoReturn:
            refuse("Design", name)

    @property
    def detail(self: Design) -> Detail:
        """The detail calls: `busbar`.

        Does not wire anything itself: each call is for a case no core call writes.
        """
        return Detail(self)
