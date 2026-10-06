"""`Design` and `Scope`: the builder, no global state (spec A1, A9); `fr.build` merges `parts`."""

import dataclasses
import itertools
from typing import TYPE_CHECKING, Any, cast, override
lazy from collections.abc import Mapping
lazy from decimal import Decimal

from fransys_model.kernel import AuthoringKey, Draft, Id, MergeConflict, Origin, Record, make_id
from fransys_model.layout import (
    BreakBefore,
    Chain,
    ChainEntry,
    KeepTogether,
    OrderHint,
    SymbolChoice,
)
from fransys_model.layout import (
    Profile as ModelProfile,
)
from fransys_model.layout import (
    SheetFormat as ModelSheetFormat,
)
from fransys_model.vocab import (
    Aspect,
    AspectNode,
    Boundary,
    CableFacet,
    Conductor,
    ConductorKind,
    FunctionKind,
    Mate,
    Net,
    NetClass,
    Placement,
    Project,
    Revision,
    UnitRelease,
    UnusedBoundary,
    instantiate,
)
from fransys_model.vocab import (
    Item as ModelItem,
)
from fransys_model.vocab import (
    Unit as ModelUnit,
)
lazy from fransys_model.vocab import Function as ModelFunction
lazy from fransys_model.vocab import Operating, Rating

from ._boundary_values import build_boundary_values
from ._catalogue import build_catalogue
from ._decimal import as_decimal
from ._enums import member
from ._keys import scoped, sorted_pair, spliced
from ._origin import caller_origin
from ._release import unit_release
from ._supply import build_supply_system
from .errors import AuthorError
from .handles import (
    Cable,
    Fn,
    Group,
    Item,
    Location,
    Port,
    Strip,
    Terminal,
    _item_from_stamped,
    _write_group_hint,
)
from .wiring import LinkScope, Wiring

if TYPE_CHECKING:
    from collections.abc import Iterable

    from _typeshed import DataclassInstance


_MINIMUM_ORDER_GROUPS = 2
_MINIMUM_BRIDGE_TERMINALS = 2
_SYMBOL_CHOICE_FIELDS = {f.name for f in dataclasses.fields(SymbolChoice)}


def _required_and_defaults(
    cls: type[DataclassInstance], *, exclude: set[str]
) -> tuple[tuple[str, ...], dict[str, Any]]:
    """The tunable fields of a record `cls` (spec A-r4): its required and its defaulted fields."""
    required: list[str] = []
    defaults: dict[str, Any] = {}
    for field_ in dataclasses.fields(cls):
        if field_.name in exclude:
            continue
        if field_.default is not dataclasses.MISSING:
            defaults[field_.name] = field_.default
        else:
            required.append(field_.name)
    return tuple(required), defaults


_SHEET_REQUIRED, _SHEET_DEFAULTS = _required_and_defaults(
    ModelSheetFormat, exclude={"id", "key", "name", "ext"}
)
_PROFILE_REQUIRED, _PROFILE_DEFAULTS = _required_and_defaults(
    ModelProfile, exclude={"id", "key", "sheet_format", "ext"}
)


@dataclasses.dataclass(frozen=True, slots=True)
class _Identity:
    name: str
    tag: str | None


def _identity(name: str | None, tag: str | None) -> _Identity:
    """Resolve `name=`/`tag=` into the key segment and the designation (spec A3)."""
    if name is not None:
        return _Identity(name=name, tag=tag)
    if tag is not None:
        return _Identity(name=tag, tag=tag)
    msg = "give name=, tag=, or both -- one is required"
    raise AuthorError(msg)


def _as_function(value: Fn | Item | Terminal) -> Fn:
    if isinstance(value, Fn):
        return value
    if isinstance(value, Item):
        return value.as_function()
    if isinstance(value, Terminal):
        return value.function
    msg = (
        f"expected a function, an item with one function, or a terminal, not {type(value).__name__}"
    )
    raise TypeError(msg)


def _with_unit(records: tuple[Record, ...], unit: Id[ModelUnit] | None) -> tuple[Record, ...]:
    """Stamp `unit` onto the `Item` record `instantiate()` made (U6, `author-0002`)."""
    if unit is None:
        return records
    return tuple(
        dataclasses.replace(record, unit=unit) if isinstance(record, ModelItem) else record
        for record in records
    )


def _with_external(records: tuple[Record, ...], *, external: bool) -> tuple[Record, ...]:
    """Stamp `external=True` onto the `Item` record only, as `_with_unit` does (spec Y1)."""
    if not external:
        return records
    return tuple(
        dataclasses.replace(record, external=True) if isinstance(record, ModelItem) else record
        for record in records
    )


class Scope(LinkScope):
    """A design-like object whose keys start with its own prefix (spec A9).

    `d.scope("p1", at=c1, group=g1)` returns one, for a reusable unit: a plain Python
    function taking a `Scope` and its own options. `at`/`group` are this scope's
    defaults for every item it creates, inherited by a nested scope unless overridden.
    """

    __slots__ = ("_at", "_design", "_group", "_prefix", "_release", "_unit")

    def __init__(  # noqa: PLR0913 -- this scope's own prefix, defaults, unit and unit release
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

    # -- structure --------------------------------------------------------------

    def location(self, name: str, description: str = "") -> Location:
        """A `+` aspect node (spec A2).

        Nests under the scope's own `at` node when it has one (units spec U6): a location
        a unit creates hangs under the location the unit was instantiated at
        (`+ER+C1-K1`). A `Design` has no `at`, so a script's top-level locations stay at
        the root, as before.
        """
        key = scoped(self._prefix, "location", name)
        node = AspectNode(
            id=make_id(AspectNode, key),
            key=key,
            aspect=Aspect.LOCATION,
            parent=self._at.id if self._at is not None else None,
            label=name,
            description=description,
        )
        self._design._add(node, caller_origin())
        return Location(id=node.id, key=key)

    def group(self, name: str, description: str = "") -> Group:
        """A `=` aspect node: a functional group (spec A2)."""
        key = scoped(self._prefix, "group", name)
        node = AspectNode(
            id=make_id(AspectNode, key),
            key=key,
            aspect=Aspect.FUNCTION,
            parent=None,
            label=name,
            description=description,
        )
        self._design._add(node, caller_origin())
        return Group(id=node.id, key=key)

    def scope(self, name: str, *, at: Location | None = None, group: Group | None = None) -> Scope:
        """A nested scope; every key it writes starts with this scope's prefix plus `name`."""
        prefix = scoped(self._prefix, name)
        return Scope(
            self._design,
            prefix,
            at=at if at is not None else self._at,
            group=group if group is not None else self._group,
            unit=self._unit,
            release=self._release,
        )

    def unit(  # noqa: PLR0913 -- the release's own five fields (SC2) plus the name
        self,
        name: str,
        *,
        version: int = 1,
        revision: int,
        interface: str,
        title: str = "",
        number: str = "",
        tag: str | None = None,
        class_code: str = "",
    ) -> Scope:
        """Write a `UnitRelease` and a `Unit` of it, and return a scope whose unit is the `Unit`.

        The release (`name`, `version`, `revision`, `interface`, `title`, `number`) is the product:
        every instance of one release writes an identical record, which the draft keeps once (SC2,
        FD4). `title` and `number` are the unit's own title and document number (UNIT-ID I1),
        default `""`; `tag` is the instance's tag (UT1); `class_code` numbers its floating
        instances (UT3). Every item created through the returned
        scope, or one nested in it, gets `unit=` the new `Unit`, whose `parent` is the unit of
        `self`, or `None`.

        Raises:
            AuthorError: this prefix already has a unit (`s.unit()` called twice).
            MergeConflict: another instance wrote a release of the same name, version and
                revision with different content; it names both origins.
        """
        key = scoped(self._prefix, "unit")
        unit_id = make_id(ModelUnit, key)
        if self._design._draft.key_of(unit_id) is not None:
            existing = cast("ModelUnit", self._design._draft.record_of(unit_id))
            existing_release = cast("UnitRelease", self._design._draft.record_of(existing.release))
            msg = f"this scope already has a unit ({existing_release.name!r}); one per prefix"
            raise AuthorError(msg)
        release = unit_release(
            name, version, revision, interface, title=title, number=number, class_code=class_code
        )
        origin = caller_origin()
        # Not `_add`: its name-clash AuthorError words a `name=` fix; a release conflict is
        # the draft's own `MergeConflict`, naming both origins.
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

    def revision(  # noqa: PLR0913 -- the revision's own seven fields (units spec U4)
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
        """Write one `Revision` history entry for this scope's own unit release (units spec U4).

        `version=None` is the release's own version. The key is scoped to the release, not to
        this scope's prefix, so every instance of one release writes identical records, which
        the draft keeps once. It never collides with the project's flat `Design.revision` key.

        Raises:
            AuthorError: this scope has no unit; call `s.unit(...)` on this scope first.
        """
        release = self._release
        if release is None:
            msg = "revision() needs a unit; call s.unit(...) on this scope first"
            raise AuthorError(msg)
        entry_version = release.version if version is None else version
        key = (*release.key, "revision", str(entry_version), str(revision))
        self._write_revision(
            key,
            release.id,
            entry_version,
            revision,
            date=date,
            text=text,
            created=created,
            checked=checked,
            approved=approved,
        )

    def _write_revision(  # noqa: PLR0913 -- the record's own eight fields plus its key
        self,
        key: AuthoringKey,
        release: Id[UnitRelease] | None,
        version: int,
        revision: int,
        *,
        date: str,
        text: str,
        created: str,
        checked: str,
        approved: str,
    ) -> None:
        record = Revision(
            id=make_id(Revision, key),
            key=key,
            release=release,
            version=version,
            revision=revision,
            date=date,
            text=text,
            created=created,
            checked=checked,
            approved=approved,
        )
        # Not `_add`: its name-clash AuthorError words a `name=` fix; two instances of one
        # release writing different entry text are the draft's own `MergeConflict` (SC2).
        self._design._draft.add(record, origin=caller_origin())

    @property
    def unit_id(self) -> Id[ModelUnit] | None:
        """This scope's own unit, or `None` (units spec U6: "the scope's `unit` attribute").

        Named `unit_id`, not `unit`: that name is already `Scope.unit(...)`, the method that
        creates a *nested* unit scope (implementer's own choice, orchestrator-approved).
        """
        return self._unit

    def boundary(
        self,
        target: Fn | Item | Terminal,
        *,
        rating: Rating | None = None,
        operating: Operating | None = None,
    ) -> None:
        """Mark `target` part of this scope's unit's interface (spec U6, U3).

        `target` is an `Fn`, or a handle whose item has exactly one `TERMINAL` or
        `CONNECTOR` function (the rule `d.mate` already uses for items). `rating` and
        `operating` (`fr.author.Rating`, `fr.author.Operating`) state what the unit says about
        this boundary; given either, one `BoundaryValuesFacet` is written beside the record.

        Raises:
            AuthorError: this scope has no unit, `target` is ambiguous, or `rating` or
                `operating` is not a `Rating` or an `Operating` or has no field set. A refused
                call writes nothing.
        """
        if self._unit is None:
            msg = "boundary() needs a unit; call s.unit(...) on this scope first"
            raise AuthorError(msg)
        fn = _as_function(target)
        key = scoped(self._prefix, "boundary", spliced(fn.key))
        record = Boundary(id=make_id(Boundary, key), key=key, unit=self._unit, function=fn.id)
        facet = build_boundary_values(key, record.id, rating, operating)
        origin = caller_origin()
        self._design._add(record, origin)
        if facet is not None:
            self._design._add(facet, origin)

    def supply(
        self,
        name: str,
        *,
        current: str,
        rails: Mapping[str, tuple[str | Decimal, int | None]],
        earthing: str = "earthed",
    ) -> None:
        """Declare a supply system and its rails (spec model-review Q2).

        `current` is `"ac"` or `"dc"`; `earthing` is `"earthed"` or `"it"`. `rails` maps each
        potential name to `(max_v, phase)`: `max_v` is a `str` or `Decimal`, and `phase` is
        degrees in multiples of 60 for an AC rail above 0 V, else `None`.

        Raises:
            AuthorError: an argument breaks a rule above, or `name` is declared twice in this
                scope with different content.
        """
        key = scoped(self._prefix, "supply", name)
        record = build_supply_system(key, name, current, rails, earthing)
        self._design._add(record, caller_origin())

    def operating(self, mpn: str | tuple[str, str], function: str) -> Operating | None:
        """The operating envelope of function template `function` of part `mpn` (spec Q6).

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

    def rating(self, mpn: str | tuple[str, str], function: str | None = None) -> Rating | None:
        """The rating of part `mpn`, or of its function template `function` (spec Q6, Q1).

        `mpn` resolves as `item()` does. With no `function` this is the part's own `Rating`.
        With one it is that function's rating: the template's, else the part's, replaced whole
        and never field by field (`effective_rating`). A read: it adds nothing to the draft, and
        it needs no unit.

        Returns:
            The `Rating`, or `None` when none applies.

        Raises:
            AuthorError: `mpn` is unknown or ambiguous, or `function` is not a `str` naming a
                function template of the part.
        """
        catalogue = self._design._catalogue
        return catalogue.rating(catalogue.find(mpn), function)

    def unused(self, target: Fn | Item | Terminal) -> None:
        """Declare `target` a boundary function left unconnected on purpose (spec U6).

        `target` follows the same rule as `boundary()`.

        Raises:
            AuthorError: `target` is ambiguous.
        """
        fn = _as_function(target)
        key = scoped(self._prefix, "unused_boundary", spliced(fn.key))
        record = UnusedBoundary(id=make_id(UnusedBoundary, key), key=key, function=fn.id)
        self._design._add(record, caller_origin())

    # -- items --------------------------------------------------------------

    def item(  # noqa: PLR0913 -- the item's identity, placement and six build facts
        self,
        mpn: str | tuple[str, str] | None,
        *,
        name: str | None = None,
        tag: str | None = None,
        at: Location | None = None,
        group: Group | None = None,
        parent: Item | None = None,
        position: int | None = None,
        description: str = "",
        installed: bool = True,
        external: bool = False,
    ) -> Item:
        """One physical thing (spec A2-A5): a part instance, or part-less with `mpn=None`.

        `external=True` marks it supplied and owned by someone else (external spec Y1).
        """
        ident = _identity(name, tag)
        key = scoped(self._prefix, ident.name)
        origin = caller_origin()
        parent_id = parent.id if parent is not None else None
        if mpn is None:
            record = ModelItem(
                id=make_id(ModelItem, key),
                key=key,
                part=None,
                parent=parent_id,
                position=position,
                tag=ident.tag,
                description=description,
                installed=installed,
                unit=self._unit,
                external=external,
            )
            self._design._add(record, origin)
            handle = Item(id=record.id, key=key, functions=())
        else:
            part = self._design._catalogue.find(mpn)
            bundle = self._design._catalogue.bundle(part)
            stamped = instantiate(
                bundle,
                key,
                tag=ident.tag,
                parent=parent_id,
                position=position,
                description=description,
                installed=installed,
            )
            stamped = _with_unit(stamped, self._unit)
            stamped = _with_external(stamped, external=external)
            self._design._extend(stamped, origin)
            handle = _item_from_stamped(key, stamped, self._design)
        self._place_and_group(handle, at=at, group=group, origin=origin)
        return handle

    def strip(
        self,
        tag: str | None,
        *,
        name: str | None = None,
        at: Location | None = None,
        external: bool = False,
        description: str = "",
    ) -> Strip:
        """A part-less terminal strip (spec A5, A7).

        `external=True` flags the strip alone; its terminals are external through the
        parent chain (external spec Y1). `description` prints at the strip's list heading.
        """
        ident = _identity(name, tag)
        key = scoped(self._prefix, ident.name)
        origin = caller_origin()
        record = ModelItem(
            id=make_id(ModelItem, key),
            key=key,
            part=None,
            parent=None,
            position=None,
            tag=ident.tag,
            description=description,
            unit=self._unit,
            external=external,
        )
        self._design._add(record, origin)
        self._place_at(record.id, key, at=at, origin=origin)
        return Strip(self._design, record.id, key, self._unit)

    def cable(  # noqa: PLR0913 -- identity, placement and the cable's own build facts
        self,
        mpn: str | tuple[str, str],
        *,
        name: str | None = None,
        tag: str | None = None,
        length_mm: int | None = None,
        at: Location | None = None,
        group: Group | None = None,
        parent: Item | None = None,
        external: bool = False,
    ) -> Cable:
        """A cable item (spec A6): `cable.core(index, a, b)` reads colour from the part.

        `external=True` flags the cable's item; its conductors carry no flag (external spec Y2).
        """
        ident = _identity(name, tag)
        key = scoped(self._prefix, ident.name)
        origin = caller_origin()
        part = self._design._catalogue.find(mpn)
        bundle = self._design._catalogue.bundle(part)
        parent_id = parent.id if parent is not None else None
        stamped = instantiate(
            bundle,
            key,
            tag=ident.tag,
            parent=parent_id,
        )
        stamped = _with_unit(stamped, self._unit)
        stamped = _with_external(stamped, external=external)
        self._design._extend(stamped, origin)
        handle = _item_from_stamped(key, stamped, self._design)
        facet_key = scoped(key, "cable_facet")
        facet = CableFacet(
            id=make_id(CableFacet, facet_key), key=facet_key, subject=handle.id, length_mm=length_mm
        )
        self._design._add(facet, origin)
        self._place(handle.id, key, at=at, default=self._at, origin=origin)
        self._place(handle.id, key, at=group, default=self._group, origin=origin)
        colours = self._design._catalogue.cable_product(part).core_colours
        return Cable(self._design, handle.id, key, colours)

    def harness(
        self,
        *,
        name: str | None = None,
        tag: str,
        at: Location | None = None,
        group: Group | None = None,
        external: bool = False,
    ) -> Item:
        """A harness item (spec A6, model decision 0026): a part-less `d.item(...)`.

        `external=True` is passed to `item` (external spec Y1).

        `tag` is required (spec H2's amendment, decision author-0003): a part-less harness
        gets no class letter from numbering, so an untagged harness would never gain a
        designation, and `derive.item_designation` now refuses to render one of its
        members instead of silently rendering it flat (model-0043's amendment).
        """
        return self.item(None, name=name, tag=tag, at=at, group=group, external=external)

    # -- connectivity --------------------------------------------------------------

    def wiring(self, *, colour: str, gauge: str | Decimal, label: str | None = None) -> Wiring:
        """A wire maker with defaults (spec A6)."""
        return Wiring(
            self._design,
            self._prefix,
            colour=colour,
            gauge=as_decimal(gauge, field="gauge"),
            label=label,
        )

    def net(
        self, name: str, *ports: Port, cls: str = "control", potential: str | None = None
    ) -> None:
        """A declared `Net` (spec A6)."""
        net_class = member(NetClass, cls, field="net class")
        key = scoped(self._prefix, "net", name)
        record = Net(
            id=make_id(Net, key),
            key=key,
            name=name,
            net_class=net_class,
            ports=tuple(port.id for port in ports),
            potential=potential,
        )
        self._design._add(record, caller_origin())

    def mate(self, a: Fn | Item, b: Fn | Item) -> None:
        """Two connector functions plugged together (spec A6)."""
        fn_a, fn_b = _as_function(a), _as_function(b)
        ends = sorted_pair(fn_a.key, fn_b.key)
        key = scoped(self._prefix, "mate", spliced(ends[0]), spliced(ends[1]))
        record = Mate(id=make_id(Mate, key), key=key, a=fn_a.id, b=fn_b.id)
        self._design._add(record, caller_origin())

    def bridge(self, *terminals: Terminal) -> None:
        """A `jumper` conductor between each consecutive pair of `terminals` (spec T1, author-0004).

        At least two terminals, all children of one strip, none repeated. Each jumper sits
        on its pair's `internal` ports, carries no `wire` facet and no label. The jumper's
        key is its pair's two terminal keys, so the same pair bridged twice is the existing
        duplicate-key error.

        Raises:
            AuthorError: fewer than two terminals, a terminal given twice, or the terminals
                are not all children of one strip.
        """
        if len(terminals) < _MINIMUM_BRIDGE_TERMINALS:
            msg = (
                f"d.bridge needs at least {_MINIMUM_BRIDGE_TERMINALS} terminals, "
                f"got {len(terminals)}"
            )
            raise AuthorError(msg)
        seen: set[Id[ModelItem]] = set()
        for terminal in terminals:
            if terminal.id in seen:
                msg = f"terminal '{'/'.join(terminal.key)}' is given twice to d.bridge"
                raise AuthorError(msg)
            seen.add(terminal.id)
        strip_keys = [self._strip_key(terminal) for terminal in terminals]
        if len(set(strip_keys)) > 1:
            named = ", ".join(
                f"'{'/'.join(terminal.key)}' (strip {_strip_text(strip_key)})"
                for terminal, strip_key in zip(terminals, strip_keys, strict=True)
            )
            msg = f"d.bridge needs terminals of one strip; got {named}"
            raise AuthorError(msg)
        origin = caller_origin()
        for a, b in itertools.pairwise(terminals):
            ends = sorted_pair(a.key, b.key)
            key = scoped(self._prefix, "jumper", spliced(ends[0]), spliced(ends[1]))
            conductor = Conductor(
                id=make_id(Conductor, key),
                key=key,
                a=a.inner.id,
                b=b.inner.id,
                kind=ConductorKind.JUMPER,
                carrier=None,
            )
            self._design._add(conductor, origin)

    def _strip_key(self, terminal: Terminal) -> AuthoringKey | None:
        """The authoring key of the item `terminal` is a child of, or `None`."""
        record = self._design._draft.record_of(terminal.id)
        if not isinstance(record, ModelItem) or record.parent is None:
            return None
        return self._design._draft.key_of(record.parent)

    # -- layout hints --------------------------------------------------------------

    def chain(self, *functions: Fn | Item | Terminal) -> None:
        """One series chain of functions, source first (spec A8)."""
        resolved = [_as_function(function) for function in functions]
        entries = tuple(
            ChainEntry(function=fn.id, index=index) for index, fn in enumerate(resolved)
        )
        key = scoped(self._prefix, "chain", *(spliced(fn.key) for fn in resolved))
        record = Chain(id=make_id(Chain, key), key=key, entries=entries)
        self._design._add(record, caller_origin())

    def keep_together(self, *groups: Group) -> None:
        """Put these `=` groups on one page when they fit (spec A8)."""
        ordered = sorted(groups, key=lambda group: group.id)
        key = scoped(self._prefix, "keep_together", *(spliced(group.key) for group in ordered))
        record = KeepTogether(
            id=make_id(KeepTogether, key), key=key, groups=tuple(group.id for group in ordered)
        )
        self._design._add(record, caller_origin())

    def break_before(self, group: Group) -> None:
        """Start a new page before this `=` group (spec A8)."""
        key = scoped(group.key, "break_before")
        record = BreakBefore(id=make_id(BreakBefore, key), key=key, group=group.id)
        self._design._add(record, caller_origin())

    def order(self, *groups: Group) -> None:
        """Draw each neighbour pair of `groups` in order (spec A8): one `order_hint` each."""
        if len(groups) < _MINIMUM_ORDER_GROUPS:
            msg = f"d.order needs at least {_MINIMUM_ORDER_GROUPS} groups, got {len(groups)}"
            raise AuthorError(msg)
        origin = caller_origin()
        for before, after in itertools.pairwise(groups):
            key = scoped(self._prefix, "order", spliced(before.key), spliced(after.key))
            record = OrderHint(
                id=make_id(OrderHint, key), key=key, before=before.id, after=after.id
            )
            self._design._add(record, origin)

    def symbol(
        self,
        target: Fn | Item | FunctionKind | str,
        symbol: str,
        port_map: dict[str, str] | None = None,
    ) -> None:
        """The library symbol for a function, every function of an item, or a whole kind (spec A8).

        An item lowers to one `layout.symbol_choice` per function of the item: the model
        has no "by part" selector this package exposes, since that could not tell one
        function of a part from another.
        """
        mapping = frozendict(port_map or {})
        origin = caller_origin()
        if isinstance(target, FunctionKind):
            self._write_symbol_choice_for_kind(target, symbol, mapping, origin)
            return
        if isinstance(target, str):
            kind = member(FunctionKind, target, field="function kind")
            self._write_symbol_choice_for_kind(kind, symbol, mapping, origin)
            return
        if isinstance(target, Fn):
            functions: tuple[Fn, ...] = (target,)
        elif isinstance(target, Item):
            functions = target.functions
        else:
            found = type(target).__name__
            msg = f"expected a function, an item, a FunctionKind or its value, not {found}"
            raise TypeError(msg)
        for function in functions:
            self._write_symbol_choice_for_function(function, symbol, mapping, origin)

    def _write_symbol_choice_for_function(
        self, function: Fn, symbol: str, port_map: frozendict[str, str], origin: Origin
    ) -> None:
        key = scoped(function.key, "symbol_choice")
        self._add_symbol_choice(
            key, function=function.id, kind=None, symbol=symbol, port_map=port_map, origin=origin
        )

    def _write_symbol_choice_for_kind(
        self, kind: FunctionKind, symbol: str, port_map: frozendict[str, str], origin: Origin
    ) -> None:
        key = scoped(self._prefix, "symbol", kind.value)
        self._add_symbol_choice(
            key, function=None, kind=kind, symbol=symbol, port_map=port_map, origin=origin
        )

    def _add_symbol_choice(  # noqa: PLR0913 -- the record's own five fields plus its origin
        self,
        key: AuthoringKey,
        *,
        function: Id[ModelFunction] | None,
        kind: FunctionKind | None,
        symbol: str,
        port_map: frozendict[str, str],
        origin: Origin,
    ) -> None:
        fields: dict[str, Any] = {
            "function": function,
            "part": None,
            "kind": kind,
            "symbol": symbol,
            "port_map": port_map,
        }
        if "template" in _SYMBOL_CHOICE_FIELDS:
            fields["template"] = None
        record = SymbolChoice(id=make_id(SymbolChoice, key), key=key, **fields)
        self._design._add(record, origin)

    def draw_in(self, function: Fn, group: Group) -> None:
        """Draw `function` with `group`, whatever its item's own `=` placement says (spec A8).

        The only way to hint a group: the straddling case (a function of one item drawn
        in another group), never a default and never written for every function of an
        item (that is `group=` on `d.item(...)`, a placement, not a hint).
        """
        _write_group_hint(self._design, function, group, caller_origin())

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

    def _place_at(
        self, item_id: Id[ModelItem], key: AuthoringKey, *, at: Location | None, origin: Origin
    ) -> None:
        self._place(item_id, key, at=at, default=self._at, origin=origin)

    def _place_and_group(
        self, item: Item, *, at: Location | None, group: Group | None, origin: Origin
    ) -> None:
        """`group=` is a placement at the `=` node (spec A8), exactly like `at=` at `+`."""
        self._place(item.id, item.key, at=at, default=self._at, origin=origin)
        self._place(item.id, item.key, at=group, default=self._group, origin=origin)


class Design(Scope):
    """The builder: holds the draft being written and the part catalogue (spec A1)."""

    __slots__ = ("_assumed_version", "_catalogue", "_draft", "_project_version")

    def __init__(self, parts: Draft) -> None:
        """Read `parts` once into a private index by `(manufacturer, mpn)` and by `mpn`."""
        self._draft = Draft()
        self._catalogue = build_catalogue(parts)
        self._project_version: int | None = None
        self._assumed_version = False
        super().__init__(self, ())

    def project(  # noqa: PLR0913 -- the title-block facts, spec's own project() shape
        self,
        *,
        title: str,
        number: str,
        customer: str,
        revision: int,
        author: str,
        notice: str = "",
        version: int = 1,
    ) -> None:
        """The title-block facts every document shows; at most one per model.

        `revision` is an int from 1 (the record refuses less) and names the current history
        entry; its date is that entry's (`revision(..., date=...)`). `notice` is the title
        block's IP notice cell text (spec page-frame R11.4); the default `""` fills an empty
        cell. `version` is the project's release version; `revision(...)` without `version=`
        writes entries of it.

        Raises:
            AuthorError: `version` is not 1 and an unversioned `d.revision(...)` was already
                written, as version 1, before this call.
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
            notice=notice,
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
        """Write one `Revision` history entry for the project (units spec U4: `release=None`).

        Unlike `Scope.revision`, a bare `Design` has no release (the project's own history, the
        valid case), so no guard. `version=None` is the project's version (`d.project(version=)`),
        or 1 when `project()` has not been called yet; `project()` then refuses another version.
        """
        entry_version = version if version is not None else self._project_version
        if entry_version is None:
            entry_version = 1
            self._assumed_version = True
        key = scoped(self._prefix, "revision", str(entry_version), str(revision))
        self._write_revision(
            key,
            None,
            entry_version,
            revision,
            date=date,
            text=text,
            created=created,
            checked=checked,
            approved=approved,
        )

    def sheet(self, name: str, **numbers: int | Decimal) -> Id[ModelSheetFormat]:
        """A `layout.sheet_format` (spec A8, A-r4).

        Raises:
            AuthorError: `numbers` is missing one of the sheet's fields, or names one
                the model does not have.
        """
        fields = _validated_fields(numbers, _SHEET_REQUIRED, _SHEET_DEFAULTS, what="sheet")
        key = scoped(self._prefix, "sheet", name)
        record = ModelSheetFormat(id=make_id(ModelSheetFormat, key), key=key, name=name, **fields)
        self._add(record, caller_origin())
        return record.id

    def profile(
        self, *, sheet: Id[ModelSheetFormat] | None = None, **numbers: int | frozendict[str, int]
    ) -> None:
        """A `layout.profile` (spec A8, A-r4); at most one per model.

        Every field not given keeps its house value; a field given replaces it whole (a
        rank map is never merged). `sheet=None` is the house sheet.

        Raises:
            AuthorError: `numbers` names a field the model does not have (A-r4: "a
                profile number the model does not have is an AuthorError").
        """
        fields = _validated_fields(numbers, _PROFILE_REQUIRED, _PROFILE_DEFAULTS, what="profile")
        key = ("profile",)
        record = ModelProfile(id=make_id(ModelProfile, key), key=key, sheet_format=sheet, **fields)
        self._add(record, caller_origin())

    def draft(self) -> Draft:
        """The `Draft` written so far; `fr.build` merges it with the part catalogue's own."""
        return self._draft

    def _add(self, record: Record, origin: Origin) -> None:
        try:
            self._draft.add(record, origin=origin)
        except MergeConflict as exc:
            raise AuthorError(_name_clash_message(record)) from exc

    def _extend(self, records: Iterable[Record], origin: Origin) -> None:
        for record in records:
            self._add(record, origin)


def _validated_fields(
    given: dict[str, Any], required: tuple[str, ...], defaults: dict[str, Any], *, what: str
) -> dict[str, Any]:
    allowed = set(required) | set(defaults)
    unknown = sorted(set(given) - allowed)
    if unknown:
        msg = f"{what}() does not have {', '.join(unknown)}; valid: {', '.join(sorted(allowed))}"
        raise AuthorError(msg)
    missing = sorted(set(required) - set(given))
    if missing:
        msg = f"{what}() is missing {', '.join(missing)}"
        raise AuthorError(msg)
    return {**defaults, **given}


def _strip_text(strip_key: AuthoringKey | None) -> str:
    return "none" if strip_key is None else "'" + "/".join(strip_key) + "'"


def _name_clash_message(record: Record) -> str:
    kind = vars(type(record)).get("__kind__", "record")
    return (
        f"'{'/'.join(record.key)}' already names a different {kind} record "
        "in this scope; use a different name= or tag="
    )
