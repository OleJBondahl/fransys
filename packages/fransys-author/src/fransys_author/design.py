"""`Design` and `Scope`: the builder, no global state; `fr.build` merges `parts`."""

import itertools
from typing import TYPE_CHECKING, cast, override

from fransys_model.kernel import AuthoringKey, Draft, Id, MergeConflictError, Origin, Record, make_id
from fransys_model.layout import OrderHint
from fransys_model.vocab import Boundary, Placement, Project, Revision, UnitRelease
from fransys_model.vocab import Item as ModelItem
from fransys_model.vocab import Unit as ModelUnit

from ._catalogue import build_catalogue
from ._design_support import _name_clash_message
from ._earth import Earths
from ._keys import scoped, spliced
from ._origin import caller_origin
from ._release import unit_release
from ._scope_build import BuildScope
from ._scope_unit import UnitScope
from ._series_blocks import SeriesBlocks
from ._supply import SupplyScope
from .errors import AuthorError
from .wiring import LinkScope

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .handles import Group, Item, Location


_MINIMUM_ORDER_GROUPS = 2


class Scope(UnitScope, BuildScope, LinkScope, SupplyScope):
    """A design-like object whose keys start with its own prefix.

    `d.scope("p1", at=c1, group=g1)` returns one, for a reusable unit: a plain Python
    function taking a `Scope` and its own options. `at`/`group` are this scope's
    defaults for every item it creates, inherited by a nested scope unless overridden.
    """

    __slots__ = ("_at", "_design", "_group", "_held", "_prefix", "_release", "_unit")

    def __init__(  # noqa: PLR0913 -- this scope's own prefix, defaults, unit and unit release [public keyword API kept, decision 0444]
        self,
        design: Design,
        prefix: AuthoringKey,
        *,
        at: Location | None = None,
        group: Group | None = None,
        unit: Id[ModelUnit] | None = None,
        release: UnitRelease | None = None,
    ) -> None:
        """Not called directly outside this package; use `Design(parts)` or `d.scope(...)`."""
        self._design = design
        self._prefix = prefix
        self._at = at
        self._group = group
        self._unit = unit
        self._release = release
        self._held: list[tuple[Boundary, Origin, bool]] | None = None

    # -- structure --------------------------------------------------------------

    def scope(self, name: str, *, at: Location | None = None, group: Group | None = None) -> Scope:
        """A nested scope; every key it writes starts with this scope's prefix plus `name`."""
        prefix = scoped(self._prefix, name)
        child = Scope(
            self._design,
            prefix,
            at=at if at is not None else self._at,
            group=group if group is not None else self._group,
            unit=self._unit,
            release=self._release,
        )
        child._held = self._held
        return child

    def unit(  # noqa: PLR0913 -- the release's own five fields plus the name [public keyword API kept, decision 0444]
        self,
        name: str,
        *,
        version: int = 1,
        revision: int,
        interface: str,
        title: str = "",
        number: str = "",
        tag: str | None = None,
    ) -> Scope:
        """Write a `UnitRelease` and a `Unit` of it, and return a scope whose unit is the `Unit`.

        The release (`name`, `version`, `revision`, `interface`, `title`, `number`) is the product:
        every instance of one release writes an identical record, which the draft keeps once.
        `title` and `number` are the unit's own title and document number, default `""`;
        `tag` is the instance's tag.
        Every item created through the returned scope, or one nested in it, gets `unit=`
        the new `Unit`, whose `parent` is the unit of `self`, or `None`.

        Raises:
            AuthorError: this prefix already has a unit (`s.unit()` called twice).
            MergeConflictError: another instance wrote a release of the same name, version and
                revision with different content; it names both origins.
        """
        key = scoped(self._prefix, "unit")
        unit_id = make_id(ModelUnit, key)
        if self._design._draft.key_of(unit_id) is not None:
            existing = cast("ModelUnit", self._design._draft.record_of(unit_id))
            existing_release = cast("UnitRelease", self._design._draft.record_of(existing.release))
            msg = f"this scope already has a unit ({existing_release.name!r}); one per prefix"
            raise AuthorError(msg)
        release = unit_release(name, version, revision, interface, title=title, number=number)
        origin = caller_origin()
        # Not `_add`: its name-clash AuthorError words a `name=` fix; a release conflict is
        # the draft's own `MergeConflictError`, naming both origins.
        self._design._draft.add(release, origin=origin)
        record = ModelUnit(id=unit_id, key=key, release=release.id, parent=self._unit, tag=tag)
        self._design._add(record, origin)
        return Scope(
            self._design,
            self._prefix,
            at=self._at,
            group=self._group,
            unit=record.id,
            release=release,
        )

    def order(self, *groups: Group) -> None:
        """Draw each neighbour pair of `groups` in order: one `order_hint` each."""
        if len(groups) < _MINIMUM_ORDER_GROUPS:
            msg = f"d.layout.order needs at least {_MINIMUM_ORDER_GROUPS} groups, got {len(groups)}"
            raise AuthorError(msg)
        origin = caller_origin()
        for before, after in itertools.pairwise(groups):
            key = scoped(self._prefix, "order", spliced(before.key), spliced(after.key))
            record = OrderHint(id=make_id(OrderHint, key), key=key, before=before.id, after=after.id)
            self._design._add(record, origin)

    # -- shared placement --------------------------------------------------------------

    def _place(
        self,
        item_id: Id[ModelItem],
        key: AuthoringKey,
        *,
        at: Location | Group | None,
        default: Location | Group | None,
        origin: Origin,
    ) -> None:
        """One `placement` of `item_id` at `at` (a `+` node or a `=` node), else `default`."""
        resolved = at if at is not None else default
        if resolved is not None:
            placement_key = scoped(key, "at", *resolved.key)
            placement = Placement(
                id=make_id(Placement, placement_key),
                key=placement_key,
                item=item_id,
                node=resolved.id,
            )
            self._design._add(placement, origin)

    def _place_and_group(self, item: Item, *, at: Location | None, group: Group | None, origin: Origin) -> None:
        """`group=` is a placement at the `=` node, exactly like `at=` at `+`."""
        self._place(item.id, item.key, at=at, default=self._at, origin=origin)
        self._place(item.id, item.key, at=group, default=self._group, origin=origin)


class Design(Scope):
    """The builder: holds the draft being written and the part catalogue."""

    __slots__ = (
        "__weakref__",
        "_added_units",
        "_assumed_version",
        "_catalogue",
        "_draft",
        "_earths",
        "_project_version",
        "_series_blocks",
    )

    def __init__(self, parts: Draft) -> None:
        """Read `parts` once into a private index by `(manufacturer, mpn)` and by `mpn`."""
        self._draft = Draft()
        self._earths = Earths()
        self._series_blocks = SeriesBlocks()
        self._catalogue = build_catalogue(parts)
        self._project_version: int | None = None
        self._assumed_version = False
        # What `d.add` returned, by id, with the unit it built.
        self._added_units: dict[int, tuple[object, Id[ModelUnit] | None]] = {}
        super().__init__(self, ())

    def project(  # noqa: PLR0913 -- the title-block facts, project()'s own shape [public keyword API kept, decision 0444]
        self,
        *,
        title: str,
        number: str,
        customer: str,
        revision: int,
        author: str,
        version: int = 1,
    ) -> None:
        """The title-block facts every document shows; at most one per model.

        `revision` names the current history entry; `version` is the release version.
        """
        if version != 1 and self._assumed_version:
            msg = (
                f"project(version={version}) came after a d.revision(...) without version=, "
                "which was written as version 1; call d.project(...) first, "
                "or pass version= to d.revision(...)"
            )
            raise AuthorError(msg)
        key = ("project",)
        record = Project(
            id=make_id(Project, key),
            key=key,
            title=title,
            number=number,
            customer=customer,
            revision=revision,
            author=author,
            version=version,
        )
        self._add(record, caller_origin())
        self._project_version = version

    @override
    def revision(
        self,
        revision: int,
        *,
        date: str,
        text: str,
        created: str,
        checked: str = "",
        approved: str = "",
        version: int | None = None,
    ) -> None:
        """Write one `Revision` history entry for the project (`release=None`).

        `version=None` is the project's version, else 1; same version and revision must match.
        """
        entry_version = version if version is not None else self._project_version
        if entry_version is None:
            entry_version = 1
            self._assumed_version = True
        key = scoped(self._prefix, "revision", str(entry_version), str(revision))
        self._write_revision(
            Revision(
                id=make_id(Revision, key),
                key=key,
                release=None,
                version=entry_version,
                revision=revision,
                date=date,
                text=text,
                created=created,
                checked=checked,
                approved=approved,
            )
        )

    def draft(self) -> Draft:
        """The `Draft` written so far; `fr.build` merges it with the part catalogue's own.

        Each scope's `d.earth` ports become its one `PE` net here, and a later `d.earth` raises.
        """
        for net, origin in self._earths.nets():
            self._add(net, origin)
        for hint, origin in self._series_blocks.resolve(self._draft):
            self._add(hint, origin)
        return self._draft

    def _add(self, record: Record, origin: Origin) -> None:
        first = self._draft.origin_of(record.id) if isinstance(record, ModelItem) else None
        try:
            self._draft.add(record, origin=origin)
        except MergeConflictError as exc:
            raise AuthorError(_name_clash_message(record)) from exc
        if first is not None:
            raise AuthorError(_name_clash_message(record, first, origin))

    def _extend(self, records: Iterable[Record], origin: Origin) -> None:
        for record in records:
            self._add(record, origin)
