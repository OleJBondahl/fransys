"""The structure and unit methods of `Scope`: nodes, units, revisions, sheets and the unit boundary."""

from typing import TYPE_CHECKING, cast

from fransys_model.kernel import Id, make_id
from fransys_model.layout import Profile as ModelProfile
from fransys_model.vocab import Aspect, AspectNode, Boundary, Revision, UnusedBoundary, UnusedPort
from fransys_model.vocab import Unit as ModelUnit
lazy from fransys_model.vocab import Operating

from ._design_support import _PROFILE_DEFAULTS, _PROFILE_REQUIRED, _as_function, _validated_fields
from ._keys import scoped, spliced
from ._origin import caller_origin
from .errors import AuthorError
from .handles import Fn, Group, Item, Location, Port, Terminal
lazy from ._decimal import ProfileNumber

if TYPE_CHECKING:
    from .design import Scope


class UnitScope:
    """The structure and unit methods of `Scope`: nodes, units, revisions, sheets and the unit boundary."""

    __slots__ = ()

    def location(self: Scope, name: str, description: str = "", outer: Location | None = None) -> Location:
        """A `+` aspect node.

        Nests under `outer`, else under the scope's own `at` node when it has one: a location a
        unit creates hangs under the location the unit was instantiated at (`+ER+C1-K1`). A
        `Design` has no `at`, so a script's top-level locations stay at the root, as before.
        """
        parent = at.id if (at := outer or self._at) else None
        node = self._aspect_node("location", Aspect.LOCATION, name, description, parent)
        return Location(id=node.id, key=node.key)

    def group(self: Scope, name: str, description: str = "") -> Group:
        """A `=` aspect node: a functional group."""
        node = self._aspect_node("group", Aspect.FUNCTION, name, description, None)
        return Group(id=node.id, key=node.key)

    def _aspect_node(
        self: Scope,
        kind: str,
        aspect: Aspect,
        name: str,
        description: str,
        parent: Id[AspectNode] | None,
    ) -> AspectNode:
        key = scoped(self._prefix, kind, name)
        node = AspectNode(
            id=make_id(AspectNode, key),
            key=key,
            aspect=aspect,
            parent=parent,
            label=name,
            description=description,
        )
        self._design._add(node, caller_origin())
        return node

    def revision(  # noqa: PLR0913 -- the revision's own seven fields [public keyword API kept, decision 0444]
        self: Scope,
        revision: int,
        *,
        date: str,
        text: str,
        created: str,
        checked: str = "",
        approved: str = "",
        version: int | None = None,
    ) -> None:
        """Write one `Revision` history entry for this scope's own unit release.

        `version=None` is the release's own version. The key is scoped to the release, not to
        this scope's prefix, so every instance of one release writes identical records, which
        the draft keeps once. It never collides with the project's flat `Design.revision` key.

        Raises:
            AuthorError: this scope has no unit; call `s.unit(...)` on this scope first.
        """
        release = self._release
        if release is None:
            msg = "a unit revision needs a unit: write this scope as a unit with @fr.unit"
            raise AuthorError(msg)
        entry_version = release.version if version is None else version
        key = (*release.key, "revision", str(entry_version), str(revision))
        self._write_revision(
            Revision(
                id=make_id(Revision, key),
                key=key,
                release=release.id,
                version=entry_version,
                revision=revision,
                date=date,
                text=text,
                created=created,
                checked=checked,
                approved=approved,
            )
        )

    def _write_revision(self: Scope, record: Revision) -> None:
        # Not `_add`: its name-clash AuthorError words a `name=` fix; two instances of one
        # release writing different entry text are the draft's own `MergeConflictError`.
        self._design._draft.add(record, origin=caller_origin())

    def profile(self: Scope, **numbers: ProfileNumber) -> None:
        """A `layout.profile`; at most one per unit, and one for the top design.

        Inside a unit body it is the unit's own profile: it governs the unit's own drawings
        wherever they are built, and the top design's never reaches them (model-0192).
        Every field not given keeps its house value; a field given replaces it whole.

        Raises:
            AuthorError: `numbers` names a field the model does not have (A-r4: "a
                profile number the model does not have is an AuthorError").
        """
        fields = _validated_fields(numbers, _PROFILE_REQUIRED, _PROFILE_DEFAULTS, what="profile")
        unit = self._unit
        key = ("profile",)
        if unit is not None:
            key = (*cast("ModelUnit", self._design._draft.record_of(unit)).key, "profile")
        record = ModelProfile(id=make_id(ModelProfile, key), key=key, unit=unit, **fields)
        self._design._add(record, caller_origin())

    @property
    def unit_id(self: Scope) -> Id[ModelUnit] | None:
        """This scope's own unit, or `None`.

        Named `unit_id`, not `unit`: that name is already `Scope.unit(...)`, the method that
        creates a *nested* unit scope (approved).
        """
        return self._unit

    def boundary(
        self: Scope,
        target: Fn | Item | Terminal,
        *,
        name: str | None = None,
    ) -> None:
        """Mark `target` part of this scope's unit's interface.

        `target` is an `Fn`, or a handle whose item has exactly one `TERMINAL` or
        `CONNECTOR` function (the rule `d.mate` already uses for items).
        `name` is the interface field name; `d.add` fills it when left `None` (model-0174).

        Raises:
            AuthorError: this scope has no unit, or `target` is ambiguous. A refused call
                writes nothing.
        """
        if self._unit is None:
            msg = "a boundary needs a unit: write this scope as a unit with @fr.unit"
            raise AuthorError(msg)
        fn = _as_function(target)
        key = scoped(self._prefix, "boundary", spliced(fn.key))
        record = Boundary(id=make_id(Boundary, key), key=key, unit=self._unit, function=fn.id, name=name)
        origin = caller_origin()
        if self._held is None:
            self._design._add(record, origin)
        else:  # `d.add` writes it once the interface names it (model-0174)
            self._held.append((record, origin, False))

    def boundary_if_returned(self: Scope, target: Fn | Item | Terminal, *, accessory: bool = False) -> None:
        """Like `boundary()`, but a unit's `d.add` writes it only if the interface holds `target`.

        A scope with no unit writes nothing for an `accessory` (an untagged device with `parent=`)
        and raises for any other; a scope not held by `d.add` writes it at once.

        Raises:
            AuthorError: this scope has no unit and `target` is no accessory's.
        """
        if self._unit is None:
            if not accessory:
                msg = (
                    "unused= on a tagged or parentless device needs a unit: write this scope "
                    "as a unit with @fr.unit, or make the device an untagged accessory with parent="
                )
                raise AuthorError(msg)
            return
        self.boundary(target)
        if self._held:
            record, origin, _ = self._held.pop()
            self._held.append((record, origin, True))

    def operating(self: Scope, mpn: str | tuple[str, str], function: str) -> Operating | None:
        """The operating envelope of function template `function` of part `mpn`.

        `mpn` resolves as `item()` does. `function` is the function template's name in the part
        file. A read: it adds nothing to the draft, and it needs no unit.

        Returns:
            The template's `Operating`, or `None` when the template states none.

        Raises:
            AuthorError: `mpn` is unknown or ambiguous, or `function` is not a `str` naming a
                function template of the part.
        """
        catalogue = self._design._catalogue
        return catalogue.operating(catalogue.find(mpn), function)

    def unused(self: Scope, target: Fn | Item | Terminal) -> None:
        """Declare `target` a boundary function left unconnected on purpose.

        `target` follows the same rule as `boundary()`.

        Raises:
            AuthorError: `target` is ambiguous, or this scope already declared it unused.
        """
        fn = _as_function(target)
        key = scoped(self._prefix, "unused_boundary", spliced(fn.key))
        record = UnusedBoundary(id=make_id(UnusedBoundary, key), key=key, function=fn.id)
        self._declare_once(record, "/".join(fn.key[:-2]))

    def unused_port(self: Scope, port: Port) -> None:
        """Declare `port` left open on purpose, so `FUNCTION_HALF_CONNECTED` stays silent for it.

        Raises:
            AuthorError: this scope already declared it unused.
        """
        key = scoped(self._prefix, "unused_port", spliced(port.key))
        self._declare_once(UnusedPort(id=make_id(UnusedPort, key), key=key, port=port.id), "/".join(port.key))

    def _declare_once(self: Scope, record: UnusedBoundary | UnusedPort, label: str) -> None:
        """Add `record`; a second one for the same point raises, naming both call lines."""
        origin = caller_origin()
        first = self._design._draft.origin_of(record.id)
        if first is not None:
            msg = (
                f"UNUSED_LISTED_TWICE: {label} is declared unused twice, first at {first.file}:{first.line}, "
                f"again at {origin.file}:{origin.line}; list each point once in d.unused(...)"
            )
            raise AuthorError(msg)
        self._design._add(record, origin)
