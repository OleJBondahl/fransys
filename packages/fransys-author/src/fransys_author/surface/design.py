"""The surface `Design`: bare tags, a default place and one function block (EA2, EA3)."""

import contextlib
import dataclasses
from typing import cast
lazy from collections.abc import Iterator

from fransys_author.design import Design as EngineDesign
from fransys_author.errors import AuthorError
lazy from fransys_author.design import Scope
lazy from fransys_author.handles import Group, Location
lazy from fransys_model.kernel import Draft

from ._coverage import Coverage
from ._device import Devices
from ._series import Series
from ._strip import Strips
from ._tags import bare
from ._units import Units
from ._wire import Wires


class Design(Devices, Wires, Strips, Series, Coverage, Units):
    """One circuit under construction, built through one engine `Design`.

    Does not start a design: call fr.design.
    """

    def __init__(
        self, library: Draft, *, place: str | None = None, scope: Scope | None = None
    ) -> None:
        """Hold `library` and the default `place`; `design()` is the one way to make this.

        `scope` is the engine scope of a unit's child (`d.add`); none makes a fresh engine.
        """
        self.library = library
        engine = EngineDesign(library) if scope is None else scope
        self._engine = cast("EngineDesign", engine)  # a unit's Scope serves the calls used here
        self._place = None if place is None else bare(place, "location")
        self._locations: dict[str, tuple[Location, str]] = {}
        self._function: str | None = None
        self._group: Group | None = None
        self._claimed: set[tuple[str | None, str]] = set()

    def location(self, name: str, text: str) -> Location:
        """Declare the place `name` (printed `+name`) with its `text`.

        Does not place anything: a device takes the default place or its own `place=`.
        """
        bare(name, "location")
        known = self._locations.get(name)
        if known is None:
            node = self._engine.location(name, text)
            self._locations[name] = (node, text)
            return node
        node, had = known
        if had and text and had != text:
            msg = (
                f"place {name!r} has the text {had!r} and was given {text!r}; a place has one text"
            )
            raise AuthorError(msg)
        if text and not had:
            records = self._engine._design.draft()._records  # N4: a place a device made first
            old = records[node.id]
            records[node.id] = dataclasses.replace(old, description=text)  # ty: ignore[invalid-argument-type] -- every Record is a dataclass
            self._locations[name] = (node, text)
        return node

    @contextlib.contextmanager
    def function(self, name: str, text: str) -> Iterator[Group]:
        """Put the devices made inside the block into function `name` (printed `=name`).

        Does not nest; the block yields the handle `d.layout` takes.
        """
        bare(name, "function")
        if self._function is not None:
            msg = f"function {name!r} inside {self._function!r}: function blocks do not nest"
            raise AuthorError(msg)
        group = self._engine.group(name, text)
        self._function, self._group = name, group
        try:
            yield group
        finally:
            self._function = self._group = None

    def draft(self) -> Draft:
        """The records written so far.

        Does not freeze them or merge the library; `fr.build` does both.
        """
        return self._engine._design.draft()

    def _place_node(self, place: str | None) -> Location | None:
        """The engine location for `place`, made on first use; `None` means no place."""
        if place is None:
            return None
        if place not in self._locations:
            self._locations[place] = (self._engine.location(place, ""), "")
        return self._locations[place][0]

    def _claim(self, tag: str, *, per_function: bool) -> str:
        """The engine key name for `tag`, claimed once: a repeat raises."""
        scope = self._function if per_function else None
        if (scope, tag) in self._claimed:
            where = f" in function {scope!r}" if scope else ""
            msg = f"tag {tag!r} is already used{where}; a tag is unique there"
            raise AuthorError(msg)
        self._claimed.add((scope, tag))
        return f"{scope}/{tag}" if scope else tag


def design(library: Draft, *, place: str | None = None) -> Design:
    """Start a circuit over the part `library`; `place` is its devices' default place.

    Does not load parts: pass the Draft the facade loaded.
    """
    return Design(library, place=place)
