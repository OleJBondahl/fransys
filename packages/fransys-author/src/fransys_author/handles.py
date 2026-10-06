"""Handles (spec A2); writes go through `_Recorder`: never import `design.py` (author-0002).

Later calls take handles, never a designation string: no code parses a designation.
"""

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Protocol
lazy from decimal import Decimal

from fransys_model.kernel import AuthoringKey, Id, make_id
from fransys_model.layout import GroupHint
from fransys_model.vocab import (
    AspectNode,
    Conductor,
    ConductorKind,
    CoreFacet,
    Function,
    FunctionKind,
    Placement,
    PlcRequestFacet,
    PortRole,
    ScalingFacet,
    SignalType,
    TerminalFacet,
)
from fransys_model.vocab import Function as ModelFunction
from fransys_model.vocab import (
    Item as ModelItem,
)
from fransys_model.vocab import (
    Port as ModelPort,
)
from fransys_model.vocab import Unit as ModelUnit
from fransys_model.vocab import instantiate as instantiate_
lazy from fransys_model.vocab import Operating, Rating

from ._decimal import as_decimal
from ._enums import member
from ._keys import scoped
from ._limits import state_limits
from ._origin import caller_origin
from .errors import AuthorError

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from fransys_model.kernel import Origin, Record

    from ._catalogue import Catalogue


class _Recorder(Protocol):
    """What a `Strip` or `Cable` needs back from the `Design` that made it."""

    @property
    def _catalogue(self) -> Catalogue: ...

    def _add(self, record: Record, origin: Origin) -> None: ...

    def _extend(self, records: Iterable[Record], origin: Origin) -> None: ...


@dataclass(frozen=True, slots=True)
class Location:
    """A `+` aspect node: where something physically is (spec A2).

    Attributes:
        id: This node's id.
        key: This node's authoring key.
    """

    id: Id[AspectNode]
    key: AuthoringKey


@dataclass(frozen=True, slots=True)
class Group:
    """A `=` aspect node: a functional group, what the layout engine calls a group.

    Attributes:
        id: This node's id.
        key: This node's authoring key.
    """

    id: Id[AspectNode]
    key: AuthoringKey


@dataclass(frozen=True, slots=True)
class Port:
    """One port of one `Fn`, reached by its marking or role.

    Attributes:
        id: This port's id.
        key: This port's authoring key.
        name: The marking `__getitem__` matches it by.
        role: What this port is for (e.g. `INTERNAL`/`EXTERNAL`).
    """

    id: Id[ModelPort]
    key: AuthoringKey
    name: str
    role: PortRole


@dataclass(frozen=True, slots=True)
class Fn:
    """One function of one item (spec A4): what `d.chain(...)` and `d.symbol(...)` name.

    Attributes:
        id: This function's id.
        key: This function's authoring key.
        item: The id of the item this function belongs to.
        name: This function's name, matched by `Item.fn`.
        kind: What kind of function this is.
        ports: This function's ports.
    """

    id: Id[ModelFunction]
    key: AuthoringKey
    item: Id[ModelItem]
    name: str
    kind: FunctionKind
    ports: tuple[Port, ...]
    _recorder: _Recorder = field(compare=False, repr=False)

    def __getitem__(self, marking: str) -> Port:
        """The port marked `marking` on this function.

        Raises `AuthorError` when no port of this function carries `marking`.
        """
        return _port_by_marking(self.ports, marking, owner="function")

    def plc(self, signal: str, signal_name: str, priority: int = 0) -> Fn:
        """Request a PLC channel of `signal` for this function (spec A7); returns `self`.

        Args:
            signal: A `SignalType` member's value (e.g. `"do"`, `"ai_current"`).
            signal_name: This channel's label, printed in the PLC report rows.
            priority: Lower goes first when `derive.allocate_plc` serves requests.

        Returns:
            This function, so calls chain.

        Raises:
            AuthorError: `signal` is not one of the model's `SignalType` values.
        """
        signal_type = member(SignalType, signal, field="PLC signal type")
        key = scoped(self.key, "plc_request")
        facet = PlcRequestFacet(
            id=make_id(PlcRequestFacet, key),
            key=key,
            subject=self.id,
            signal=signal_type,
            signal_name=signal_name,
            priority=priority,
        )
        self._recorder._add(facet, caller_origin())
        return self

    def scale(
        self, unit: str, *, raw: tuple[int, int], eng: tuple[str | Decimal, str | Decimal]
    ) -> Fn:
        """Engineering-unit scaling for this function (spec A7); returns `self`.

        Args:
            unit: The engineering unit's name (e.g. `"bar"`).
            raw: The raw signal's `(low, high)` pair.
            eng: The engineering value's `(low, high)` pair, matching `raw` (`str` or
                `Decimal`, never `float`).

        Raises:
            AuthorError: `eng` holds a `float`.
        """
        key = scoped(self.key, "scaling")
        facet = ScalingFacet(
            id=make_id(ScalingFacet, key),
            key=key,
            subject=self.id,
            unit=unit,
            raw_min=raw[0],
            raw_max=raw[1],
            eng_min=as_decimal(eng[0], field="eng"),
            eng_max=as_decimal(eng[1], field="eng"),
        )
        self._recorder._add(facet, caller_origin())
        return self


@dataclass(frozen=True, slots=True)
class Item:
    """One physical thing (spec A2): the item `d.item(...)` (or `d.harness(...)`) stamped.

    Attributes:
        id: This item's id.
        key: This item's authoring key.
        functions: This item's functions, sorted by id.
    """

    id: Id[ModelItem]
    key: AuthoringKey
    functions: tuple[Fn, ...]

    def fn(self, name: str) -> Fn:
        """The function of this item named `name` (spec A4).

        Args:
            name: A function name of this item.

        Returns:
            That function.

        Raises:
            AuthorError: no function of this item is named `name`.
        """
        for function in self.functions:
            if function.name == name:
                return function
        names = ", ".join(sorted(f.name for f in self.functions)) or "none"
        msg = f"this item has no function named {name!r}; it has: {names}"
        raise AuthorError(msg)

    def __getitem__(self, marking: str) -> Port:
        """The port marked `marking` on any function of this item (spec A4).

        Raises:
            AuthorError: no port of the item carries `marking`, or two functions of it do
                (write `item.fn("<name>")[marking]` instead).
        """
        ports = [port for function in self.functions for port in function.ports]
        return _port_by_marking(ports, marking, owner="item")

    def as_function(self) -> Fn:
        """This item's one function, for a call that expects a function (spec A4).

        Raises:
            AuthorError: the item has zero, or more than one, function.
        """
        if len(self.functions) != 1:
            count = len(self.functions)
            msg = f"an item stands in for a function only with exactly one; this has {count}"
            raise AuthorError(msg)
        return self.functions[0]


@dataclass(frozen=True, slots=True)
class Terminal:
    """One terminal of a `Strip`: one function, ports `inner`/`outer`.

    Attributes:
        id: This terminal's id.
        key: This terminal's authoring key.
        function: This terminal's one function, whose ports `inner` and `outer` reach.
    """

    id: Id[ModelItem]
    key: AuthoringKey
    function: Fn
    _scope: Any = field(
        default=None, init=False, compare=False, repr=False
    )  # the unit scope `limits` writes to; the surface sets it after making the terminal

    @property
    def inner(self) -> Port:
        """The `internal` (panel-wiring side) port (spec A2).

        Returns:
            This terminal's `internal` port.

        Raises:
            AuthorError: this terminal's function has no `internal` port.
        """
        return _port_by_role(self.function.ports, PortRole.INTERNAL)

    @property
    def outer(self) -> Port:
        """The `external` (field-cable side) port (spec A2).

        Returns:
            This terminal's `external` port.

        Raises:
            AuthorError: this terminal's function has no `external` port.
        """
        return _port_by_role(self.function.ports, PortRole.EXTERNAL)

    def limits(
        self, *, rating: Rating | None = None, operating: Operating | None = None
    ) -> Terminal:
        """State the values a unit says about this terminal's boundary: `X1[1].limits(rating=...)`.

        Does not mark the boundary: `interface=True` on the strip does.

        Raises:
            AuthorError: no value is given, or the terminal is not in a unit.
        """
        state_limits("/".join(self.key), self.function, self._scope, rating, operating)
        return self


def as_port(value: Port | Terminal) -> Port:
    """`value` as a port; a `Terminal` has two, so it is refused with the choice named."""
    if isinstance(value, Terminal):
        msg = (
            f"terminal '{'/'.join(value.key)}' is not a port: use `.inner` "
            "(a wire inside the cabinet) or `.outer` (a cable core to the field)"
        )
        raise AuthorError(msg)
    return value


@dataclass(slots=True)
class Strip:
    """A part-less item that only holds terminals (spec A5, A7): `d.strip(tag)`.

    Attributes:
        id: This strip's id.
        key: This strip's authoring key.
    """

    _recorder: _Recorder
    id: Id[ModelItem]
    key: AuthoringKey
    _unit: Id[ModelUnit] | None
    _counters: dict[str, int] = field(default_factory=dict)

    def terminal(
        self,
        mpn: str | tuple[str, str],
        group_text: str = "",
        *,
        index: int | None = None,
        group: Group | None = None,
    ) -> Terminal:
        """One terminal on this strip (spec A7).

        Args:
            mpn: The part's MPN, or `(manufacturer, mpn)` when a bare MPN is ambiguous.
            group_text: This terminal's group text; terminals that share one count up together.
            index: 1-based position within `group_text` (in the key); counts up unless given.
            group: A `=` node this terminal is placed at.

        Returns:
            The new terminal.

        Raises:
            AuthorError: `mpn` is unknown or ambiguous across manufacturers (`Catalogue.find`),
                or its part has zero or more than one function (`Item.as_function`).
        """
        if index is None:
            index = self._counters.get(group_text, 0) + 1
        self._counters[group_text] = max(self._counters.get(group_text, 0), index)
        # AuthoringKey segments must be non-empty (model design/kernel-records.md 5.2), so an empty
        # (the default) `group_text` contributes no segment of its own.
        middle = (group_text,) if group_text else ()
        key = scoped(self.key, "terminal", *middle, str(index))
        origin = caller_origin()
        part = self._recorder._catalogue.find(mpn)
        bundle = self._recorder._catalogue.bundle(part)
        stamped = instantiate_(bundle, key, parent=self.id)
        if self._unit is not None:
            stamped = tuple(
                replace(record, unit=self._unit) if isinstance(record, ModelItem) else record
                for record in stamped
            )
        self._recorder._extend(stamped, origin)
        item = _item_from_stamped(key, stamped, self._recorder)
        facet_key = scoped(key, "facet")
        facet = TerminalFacet(
            id=make_id(TerminalFacet, facet_key),
            key=facet_key,
            subject=item.id,
            group=group_text,
            index=index,
        )
        self._recorder._add(facet, origin)
        if group is not None:
            _write_placement(self._recorder, item.id, item.key, group, origin)
        return Terminal(id=item.id, key=item.key, function=item.as_function())


@dataclass(slots=True)
class Cable:
    """A cable item (spec A6): `d.cable(mpn, ...)`, then `cable.core(index, a, b)`.

    Attributes:
        id: This cable's id.
        key: This cable's authoring key.
    """

    _recorder: _Recorder
    id: Id[ModelItem]
    key: AuthoringKey
    _core_colours: tuple[str, ...]

    def core(self, index: int, a: Port, b: Port) -> None:
        """Core `index` of this cable, between `a` and `b`; its colour is the part's.

        Args:
            index: The 1-based core number.
            a: The port at one end.
            b: The port at the other end.

        Raises:
            AuthorError: `index` is not one of this cable's cores.
        """
        if not 1 <= index <= len(self._core_colours):
            msg = f"core {index} is out of range: this cable has {len(self._core_colours)} core(s)"
            raise AuthorError(msg)
        a, b = as_port(a), as_port(b)
        key = scoped(self.key, "core", str(index))
        conductor = Conductor(
            id=make_id(Conductor, key),
            key=key,
            a=a.id,
            b=b.id,
            kind=ConductorKind.CORE,
            carrier=self.id,
        )
        origin = caller_origin()
        self._recorder._add(conductor, origin)
        facet_key = scoped(key, "facet")
        facet = CoreFacet(
            id=make_id(CoreFacet, facet_key),
            key=facet_key,
            subject=conductor.id,
            index=index,
        )
        self._recorder._add(facet, origin)


def _write_group_hint(recorder: _Recorder, function: Fn, group: Group, origin: Origin) -> None:
    """Write one `layout.group_hint` for `function` (spec A8, `d.draw_in`)."""
    key = scoped(function.key, "group_hint")
    hint = GroupHint(id=make_id(GroupHint, key), key=key, function=function.id, group=group.id)
    recorder._add(hint, origin)


def _write_placement(
    recorder: _Recorder,
    item_id: Id[ModelItem],
    item_key: AuthoringKey,
    node: Location | Group,
    origin: Origin,
) -> None:
    """One `placement` of `item_id` at `node`, a `+` or `=` node (spec A8: `group=` on an item)."""
    key = scoped(item_key, "at", *node.key)
    placement = Placement(id=make_id(Placement, key), key=key, item=item_id, node=node.id)
    recorder._add(placement, origin)


def _item_from_stamped(key: AuthoringKey, stamped: tuple[Record, ...], recorder: _Recorder) -> Item:
    """Build an `Item` handle from the records `instantiate()` (or a part-less item) gave."""
    functions_by_id: dict[Id[ModelFunction], ModelFunction] = {}
    ports_by_function: dict[Id[ModelFunction], list[Port]] = {}
    for record in stamped:
        if isinstance(record, Function):
            functions_by_id[record.id] = record
        elif isinstance(record, ModelPort):
            ports_by_function.setdefault(record.function, []).append(
                Port(id=record.id, key=record.key, name=record.name, role=record.role)
            )
    functions = tuple(
        Fn(
            id=function.id,
            key=function.key,
            item=function.item,
            name=function.name,
            kind=function.kind,
            ports=tuple(ports_by_function.get(function.id, ())),
            _recorder=recorder,
        )
        for function in sorted(functions_by_id.values(), key=lambda f: f.id)
    )
    return Item(id=make_id(ModelItem, key), key=key, functions=functions)


def _port_by_marking(ports: Sequence[Port], marking: str, *, owner: str) -> Port:
    matches = [port for port in ports if port.name == marking]
    if not matches:
        markings = ", ".join(sorted({port.name for port in ports})) or "none"
        msg = f"this {owner} has no port marked {marking!r}; it has: {markings}"
        raise AuthorError(msg)
    if len(matches) > 1:
        msg = (
            f"port {marking!r} is ambiguous on this {owner}: two functions carry it; "
            f'write item.fn("<function name>")[{marking!r}] instead'
        )
        raise AuthorError(msg)
    return matches[0]


def _port_by_role(ports: Sequence[Port], role: PortRole) -> Port:
    matches = [port for port in ports if port.role is role]
    if not matches:
        msg = f"this terminal has no {role.value} port"
        raise AuthorError(msg)
    return matches[0]
