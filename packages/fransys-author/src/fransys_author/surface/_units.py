"""Surface mixin for `@unit` and `d.add`."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Callable, Mapping, Sequence
lazy from types import EllipsisType

from fransys_author.errors import AuthorError

from ._boundary_names import write_boundaries
from ._unit_tags import check_add, class_code_of
from ._unused import mark_unused
lazy from ._rows import RowValue, WiringRow

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
    wiring: Mapping[WiringRow, RowValue] | None


def unit[R: tuple[Any, ...]](  # noqa: PLR0913 -- the release's own fields
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
    wiring: Mapping[WiringRow, RowValue] | None = None,
) -> Callable[[Callable[..., R]], UnitDef[R]]:
    """Core: make a function the unit release `name`.

    It takes a child design and returns its interface.

    The interface is an instance of a `typing.NamedTuple` class, one field per boundary.

    Does not build anything: `d.add(fn, "U1")` does. `history` entries take `d.revision`'s keywords.
    `class_code` (1-3 uppercase letters) is the letter floating instances number from.
    `wiring` replaces IEC rows in the unit's body; a unit never takes its parent's rows.
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
        wiring,
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
        check_history(definition)
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
        result = definition.build(type(self)(self.library, scope=scope, wiring=definition.wiring))
        if not (isinstance(result, tuple) and hasattr(result, "_fields")):
            msg = (
                f"unit {definition.name!r} must return an instance of a typing.NamedTuple class, "
                f"not {type(result).__name__}: class Io(NamedTuple): X1: fr.Device, "
                "then return Io(X1=d.device(...))"
            )
            raise AuthorError(msg)
        write_boundaries(scope, result)
        scope._design._added_units[id(result)] = (result, scope._unit)
        mark_unused(self, scope, result, unused)
        return result
