"""The build methods of `Scope`: items, strips, cables, harnesses and their wires."""

import itertools
from typing import TYPE_CHECKING
lazy from decimal import Decimal

from fransys_model.kernel import AuthoringKey, Id, make_id
from fransys_model.layout import PoleGroup
from fransys_model.vocab import CableFacet, Conductor, ConductorKind, Mate, Net, NetClass, RailGroup
from fransys_model.vocab import Item as ModelItem

from ._decimal import as_decimal
from ._design_support import _as_function, _identity, _stamped, _strip_text
from ._enums import member
from ._keys import scoped, sorted_pair, spliced
from ._origin import caller_origin
from .errors import AuthorError
from .handles import Cable, Fn, Group, Item, Location, Port, Strip, Terminal, _item_from_stamped
from .instantiate import instantiate
from .wiring import WireHints, Wiring

if TYPE_CHECKING:
    from fransys_model.kernel import Origin, Record

    from .design import Scope


_MINIMUM_BRIDGE_TERMINALS = 2


class BuildScope:
    """The build methods of `Scope`: items, strips, cables, harnesses and their wires."""

    __slots__ = ()

    def item(  # noqa: PLR0913 -- the item's identity, placement and six build facts [public keyword API kept, decision 0444]
        self: Scope,
        mpn: str | tuple[str, str] | None,
        *,
        name: str | None = None,
        tag: str | None = None,
        at: Location | None = None,
        group: Group | None = None,
        parent: Item | Strip | None = None,
        position: int | None = None,
        description: str = "",
        installed: bool = True,
        external: bool = False,
    ) -> Item:
        """One physical thing: a part instance, or part-less with `mpn=None`.

        `external=True` marks it supplied and owned by someone else.
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
            handle = self._extend_stamped(key, stamped, origin, external=external)
        self._place_and_group(handle, at=at, group=group, origin=origin)
        return handle

    def _extend_stamped(self: Scope, key: AuthoringKey, stamped: tuple[Record, ...], origin: Origin, *, external: bool) -> Item:
        """Mark `stamped` with this scope's unit, add it to the design and return its item handle."""
        stamped = _stamped(stamped, unit=self._unit, external=external)
        self._design._extend(stamped, origin)
        return _item_from_stamped(key, stamped, self._design)

    def strip(
        self: Scope,
        tag: str | None,
        *,
        name: str | None = None,
        at: Location | None = None,
        external: bool = False,
        description: str = "",
    ) -> Strip:
        """A part-less terminal strip.

        `external=True` flags the strip alone; its terminals are external through the
        parent chain. `description` prints at the strip's list heading.
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
        self._place(record.id, key, at=at, default=self._at, origin=origin)
        return Strip(self._design, record.id, key, self._unit)

    def cable(  # noqa: PLR0913 -- identity, placement and the cable's own build facts [public keyword API kept, decision 0444]
        self: Scope,
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
        """A cable item: `cable.core(index, a, b)` reads colour from the part.

        `external=True` flags the cable's item; its conductors carry no flag.
        """
        ident = _identity(name, tag)
        key = scoped(self._prefix, ident.name)
        origin = caller_origin()
        part = self._design._catalogue.find(mpn)
        bundle = self._design._catalogue.bundle(part)
        parent_id = parent.id if parent is not None else None
        stamped = instantiate(bundle, key, tag=ident.tag, parent=parent_id)
        handle = self._extend_stamped(key, stamped, origin, external=external)
        facet_key = scoped(key, "cable_facet")
        facet = CableFacet(id=make_id(CableFacet, facet_key), key=facet_key, subject=handle.id, length_mm=length_mm)
        self._design._add(facet, origin)
        self._place(handle.id, key, at=at, default=self._at, origin=origin)
        self._place(handle.id, key, at=group, default=self._group, origin=origin)
        colours = self._design._catalogue.cable_product(part).core_colours
        return Cable(self._design, handle.id, key, colours)

    def harness(
        self: Scope,
        *,
        name: str | None = None,
        tag: str,
        at: Location | None = None,
        group: Group | None = None,
        external: bool = False,
    ) -> Item:
        """A harness item: a part-less `d.item(...)`.

        `external=True` is passed to `item`.

        `tag` is required: a part-less harness
        gets no class letter from numbering, so an untagged harness would never gain a
        designation, and `derive.item_designation` now refuses to render one of its
        members instead of silently rendering it flat (model-0043's amendment).
        """
        return self.harness_item(name, tag, at, group, external=external)

    def wiring(self: Scope, *, colour: str, gauge: str | Decimal, label: str | None = None) -> Wiring:
        """A wire maker with defaults."""
        return Wiring(
            self._design,
            self._prefix,
            colour=colour,
            gauge=as_decimal(gauge, field="gauge"),
            label=label,
        )

    def _wire_hints(self: Scope) -> WireHints:
        """A maker for a wire whose row is resolved after freeze (model-0260)."""
        return WireHints(self._design, self._prefix)

    def net(self: Scope, name: str, *ports: Port, cls: str = "control", potential: str | None = None) -> None:
        """A declared `Net`."""
        net_class = member(NetClass, cls, field="net class")
        if name == "PE":
            self._design._earths.refuse_net(self._prefix)
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

    def earth(self: Scope, *ports: Port) -> None:
        """Collect `ports` for the scope's one `PE` net, which the draft gets when it is read."""
        ids = tuple(p.id for p in ports)
        self._design._earths.collect(self._prefix, ids, caller_origin(), self._design._draft)

    def mate(self: Scope, a: Fn | Item, b: Fn | Item) -> None:
        """Two CONNECTOR or TERMINAL functions plugged together; others are refused."""
        fn_a, fn_b = _as_function(a), _as_function(b)
        ends = sorted_pair(fn_a.key, fn_b.key)
        key = scoped(self._prefix, "mate", spliced(ends[0]), spliced(ends[1]))
        record = Mate(id=make_id(Mate, key), key=key, a=fn_a.id, b=fn_b.id)
        self._design._add(record, caller_origin())

    def pole_group(self: Scope, functions: tuple[Fn, ...], *, selector: bool) -> None:
        """A `PoleGroup` of one device's one-pole contacts, in pole order (C6.4)."""
        key = scoped(functions[0].key, "pole_group")
        ids = tuple(fn.id for fn in functions)
        record = PoleGroup(id=make_id(PoleGroup, key), key=key, functions=ids, selector=selector)
        self._design._add(record, caller_origin())

    def bridge(self: Scope, *terminals: Terminal) -> None:
        """A `jumper` conductor between each consecutive pair of `terminals`.

        At least two terminals, all children of one strip, none repeated. Each jumper sits
        on its pair's `internal` ports, carries no `wire` facet and no label. The jumper's
        key is its pair's two terminal keys, so the same pair bridged twice is the existing
        duplicate-key error.

        Raises:
            AuthorError: fewer than two terminals, a terminal given twice, or the terminals
                are not all children of one strip.
        """
        self._check_bridge(terminals)
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

    def rail(self: Scope, *terminals: Terminal) -> None:
        """One `RailGroup` over `terminals`: the bridged group the engineer declares a power rail.

        All terminals are children of one strip, none repeated; one terminal is allowed.
        """
        if len(terminals) > 1:
            self._check_bridge(terminals)
        key = scoped(self._prefix, "rail", spliced(terminals[0].key))
        record = RailGroup(id=make_id(RailGroup, key), key=key, terminals=tuple(t.id for t in terminals))
        self._design._add(record, caller_origin())

    def _check_bridge(self: Scope, terminals: tuple[Terminal, ...]) -> None:
        """Refuse fewer than two terminals, a repeated terminal, or terminals of several strips."""
        if len(terminals) < _MINIMUM_BRIDGE_TERMINALS:
            msg = (
                f"a bridge needs at least {_MINIMUM_BRIDGE_TERMINALS} terminals, "
                f"got {len(terminals)}; "
                "bridge a strip with d.terminal_strip(bridged=...)"
            )
            raise AuthorError(msg)
        seen: set[Id[ModelItem]] = set()
        for terminal in terminals:
            if terminal.id in seen:
                msg = f"terminal '{'/'.join(terminal.key)}' is given twice to a bridge"
                raise AuthorError(msg)
            seen.add(terminal.id)
        strip_keys = [self._strip_key(terminal) for terminal in terminals]
        if len(set(strip_keys)) > 1:
            named = ", ".join(
                f"'{'/'.join(terminal.key)}' (strip {_strip_text(strip_key)})" for terminal, strip_key in zip(terminals, strip_keys, strict=True)
            )
            msg = f"a bridge needs terminals of one strip; got {named}"
            raise AuthorError(msg)

    def _strip_key(self: Scope, terminal: Terminal) -> AuthoringKey | None:
        """The authoring key of the item `terminal` is a child of, or `None`."""
        record = self._design._draft.record_of(terminal.id)
        if not isinstance(record, ModelItem) or record.parent is None:
            return None
        return self._design._draft.key_of(record.parent)
