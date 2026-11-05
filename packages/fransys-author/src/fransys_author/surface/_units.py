"""Surface mixin for `@unit` and `d.add`."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast
lazy from collections.abc import Callable, Mapping, Sequence
lazy from types import EllipsisType

from fransys_author.errors import AuthorError
from fransys_author.handles import Port

from ._added import remember_added
from ._boundary_names import write_boundaries
from ._unit_tags import check_add
lazy from ._unused import UnitResult, _own

if TYPE_CHECKING:
    from fransys_author.handles import Terminal
    from fransys_author.surface._device import Device
    from fransys_author.surface._handles import Fn
    from fransys_author.surface._strip import TerminalStrip
    from fransys_author.surface.design import Design


@dataclass(frozen=True, slots=True)
class UnitDef[R: tuple[Any, ...]]:
    """A function made a unit by `@unit`: the release facts `d.add` writes.

    Does not run the function; `d.add` builds the child and calls it.
    """

    build: Callable[[Any], R]
    name: str
    revision: int
    interface_version: str
    entry: Mapping[str, Any]
    version: int
    title: str
    number: str
    history: tuple[Mapping[str, Any], ...]


def unit[R: tuple[Any, ...]](  # noqa: PLR0913 -- the release's own fields [public keyword API kept, decision 0444]
    name: str,
    *,
    revision: int,
    interface_version: int | str,
    date: str,
    text: str,
    by: str,
    version: int = 1,
    title: str = "",
    number: str = "",
    history: Sequence[Mapping[str, str | int]] = (),
) -> Callable[[Callable[..., R]], UnitDef[R]]:
    """Core: make a function the unit release `name`.

    It takes a child design and returns its interface.

    The interface is an instance of a `typing.NamedTuple` class, one field per boundary.

    Does not build anything: `d.add(fn, "U1")` does. `history` entries take `d.revision`'s keywords.
    A `history=` entry with no `version` is numbered as this unit's own `version`; two entries of
    one version and revision must match, else `d.add` raises (`AuthorError` for the unit's own
    current revision, `MergeConflictError` for another).
    """
    entry = {"revision": revision, "date": date, "text": text, "created": by}
    return lambda build: UnitDef(
        build,
        name,
        revision,
        str(interface_version),
        entry,
        version,
        title,
        number,
        tuple(history),
    )


def check_history(definition: UnitDef[Any]) -> None:
    """Raise `AuthorError` for a history entry that meets the release's own revision record."""
    own = definition.entry
    for entry in definition.history:
        version = entry.get("version", definition.version)
        if (version, entry["revision"]) != (definition.version, definition.revision):
            continue
        if {k: v for k, v in entry.items() if k != "version"} == own:
            continue
        msg = (
            f"unit {definition.name!r}: history entry {version}.{entry['revision']} "
            f"({entry['text']!r}) is also the unit's own current revision record; "
            "give the entry its old `version=`"
        )
        raise AuthorError(msg)


class Units:
    """The `add` call of `Design`."""

    def add[R: tuple[Any, ...]](
        self: "Design",
        definition: UnitDef[R],
        tag: str,
        *,
        place: str | EllipsisType | None = ...,
        name: str | None = None,
    ) -> R:
        """Build the unit `definition` as instance `tag` (printed `-tag`).

        Does not take a lowercase tag. Returns the unit function's result; `name=` as in `device`.
        """
        check_history(definition)
        key = self._claim(check_add(tag, name), per_function=True)
        where = self._place if place is ... else place
        scope = self._engine.scope(key, at=self._place_node(where), group=self._group).unit(
            definition.name,
            version=definition.version,
            revision=definition.revision,
            interface=definition.interface_version,
            title=definition.title,
            number=definition.number,
            tag=tag,
        )
        for entry in (*definition.history, definition.entry):
            scope.revision(**entry)
        scope._held = []
        result = definition.build(type(self)(self.library, scope=scope))
        if not (isinstance(result, tuple) and hasattr(result, "_fields")):
            msg = (
                f"unit {definition.name!r} must return an instance of a typing.NamedTuple class, "
                f"not {type(result).__name__}: class Io(NamedTuple): X1: fr.Device, "
                "then return Io(X1=d.device(...))"
            )
            raise AuthorError(msg)
        fields = cast("UnitResult", result)  # the check above: a NamedTuple instance
        write_boundaries(scope, fields)
        remember_added(scope._design, result, scope._unit)
        return result

    def unused(self: "Design", *points: "Device | Fn | Port | Terminal | TerminalStrip") -> None:
        """Declare the boundary points of nested units that this design leaves open on purpose.

        Each point is a field of a unit `d.add` returned (`pc.x3[3]`, `pc.x4_1`); a strip or device names all its functions.
        Does not take a name or a string.
        Does not declare a unit's own open pins: that is `unused=` where the device is made.
        """
        for index, point in enumerate(points, 1):
            if isinstance(point, Port):
                self._engine.unused_port(point)
                continue
            for fn in _own(point, f"d.unused argument {index}", None):
                self._engine.unused(fn)
