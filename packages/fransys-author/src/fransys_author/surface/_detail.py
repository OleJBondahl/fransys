"""`d.detail`: the calls for a case no core call writes (author-0042, API-CLARITY C2)."""

from typing import TYPE_CHECKING, NoReturn

from fransys_author.errors import AuthorAttributeError
from fransys_author.surface._wire import _port
lazy from fransys_author.handles import Port, Terminal

if TYPE_CHECKING:
    from fransys_author.surface.design import Design

MOVED_SECTION = "the-detail-calls"  # the heading of moving-to-0.19.md the raise points to


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


class _Moved:
    """A name that moved to `d.detail`: looking it up raises and names the new home."""

    def __init__(self, core_path: str = "") -> None:
        self._core_path = core_path

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, _instance: object, owner: type | None = None) -> NoReturn:
        name = self._name
        path = f"; a current path is {self._core_path}:" if self._core_path else ":"
        msg = f"d.{name} moved to d.detail.{name} in 0.19.0{path} see moving-to-0.19#{MOVED_SECTION}"
        raise AuthorAttributeError(msg)


class Details:
    """The `detail` property of the surface `Design`, and the name that left `d`."""

    busbar = _Moved()

    @property
    def detail(self: Design) -> Detail:
        """The detail calls: `busbar`.

        Does not wire anything itself: each call is for a case no core call writes.
        """
        return Detail(self)
