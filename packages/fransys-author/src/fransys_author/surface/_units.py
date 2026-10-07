"""Surface mixin for EA-UNITS: `@unit` and `d.add` (EA8)."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Callable, Mapping, Sequence
lazy from types import EllipsisType

from fransys_author.errors import AuthorError

from ._boundary_names import write_boundaries
from ._unit_tags import check_add, class_code_of
from ._unused import mark_unused

if TYPE_CHECKING:
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
    class_code: str


def unit[R: tuple[Any, ...]](  # noqa: PLR0913 -- the release's own fields (EA8)
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
    class_code: str | None = None,
) -> Callable[[Callable[..., R]], UnitDef[R]]:
    """Make a function the unit release `name`; it takes a child design, returns its interface.

    The interface is an instance of a `typing.NamedTuple` class, one field per boundary.

    Does not build anything: `d.add(fn, "U1")` does. `history` entries take `d.revision`'s keywords.
    `class_code` (1-3 uppercase letters) is the letter floating instances number from.
    """
    code = class_code_of(class_code)
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
        code,
    )


class Units:
    """The `add` call of `Design`."""

    def add[R: tuple[Any, ...]](
        self: "Design",
        definition: UnitDef[R],
        tag: str | None,
        *,
        place: str | EllipsisType | None = ...,
        name: str | None = None,
        unused: tuple[str, ...] = (),
    ) -> R:
        """Build the unit `definition` as instance `tag` (printed `-tag`), `None` to be numbered.

        Does not take a lowercase tag. Returns the unit function's result; `name=` as in `device`.
        `unused=` names fields (`"X1"`, a terminal, run or strip) or functions (`"X1.x1"`).
        """
        key = self._claim(
            check_add(definition.name, definition.class_code, tag, name), per_function=True
        )
        where = self._place if place is ... else place
        scope = self._engine.scope(key, at=self._place_node(where), group=self._group).unit(
            definition.name,
            version=definition.version,
            revision=definition.revision,
            interface=definition.interface_version,
            title=definition.title,
            number=definition.number,
            tag=tag,
            class_code=definition.class_code,
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
        write_boundaries(scope, result)
        mark_unused(self, scope, result, unused)
        return result
