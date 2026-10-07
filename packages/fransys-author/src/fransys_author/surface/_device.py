"""Devices: `d.device("Q1", part)` and the checked references on what it returns (EA4)."""

from typing import TYPE_CHECKING, Any, overload
lazy from collections.abc import Mapping
lazy from types import EllipsisType

from fransys_author.errors import AuthorError
from fransys_author.surface._handles import Fn, Pin, pick
from fransys_author.surface._tags import bare
lazy from fransys_author.design import Scope
lazy from fransys_author.handles import Item, Strip, Terminal
lazy from fransys_author.surface import _contacts
lazy from fransys_author.surface._joins import fit_leads
lazy from fransys_author.surface._mount import mount
lazy from fransys_author.surface._parent import parent_item
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab import Item as ModelItem

if TYPE_CHECKING:
    from fransys_author.surface._strip import TerminalStrip
    from fransys_author.surface.design import Design


class Device:
    """One device: `Q1`. A function by name (`Q1.coil`), a pin by `[ ]` (`Q1[2]`, `Q1["A1"]`).

    Does not guess: an unknown function or pin raises and lists the candidates.
    """

    def __init__(self, label: str, item: Item, scope: Scope | None = None) -> None:
        """Wrap the engine `item` as `label`, made in the engine `scope`; `d.device` makes these."""
        self._label, self._item, self._scope = label, item, scope

    @property
    def id(self) -> Id[ModelItem]:
        """The model id of the device, the key `fr.derive` reads it by after a build.

        Does not change between the draft and the built model.
        """
        return self._item.id

    def _pins(self) -> list[tuple[str, Pin]]:
        return [(f.name, pin) for f in self._item.functions for pin in f.ports]

    if not TYPE_CHECKING:  # a typed part declares its functions and pins; ty must see no catch-all

        def __getitem__(self, marking: str | int) -> Pin:
            """The pin marked `marking` on any function; an integer needs no quotes.

            Does not guess: an unknown or doubled marking raises and names the candidates.
            """
            return pick(self._label, str(marking), self._pins())

        def __getattr__(self, name: str) -> Fn | Pin:
            """The function `name` (`Q1.coil`), else the one pin of that name (`Q1.A1`).

            Does not guess: an unknown name raises and lists the functions.
            """
            if name.startswith("_"):
                raise AttributeError(name)
            for function in self._item.functions:
                if function.name == name:
                    return Fn(self._label, function, self._scope)
            if any(pin.name == name for _, pin in self._pins()):
                return pick(self._label, name, self._pins())
            names = ", ".join(sorted(f.name for f in self._item.functions))
            msg = f"{self._label} has no function or pin {name!r}; functions: {names}"
            raise AuthorError(msg)


class TypedFn(Fn):
    """The base a generated module subclasses for one function of one part.

    Does not add behaviour: its subclass only declares pins for the type checker.
    """


class TypedDevice[N: str = str, S = Any](Device):
    """The base a generated module subclasses for one part; `mpn` is its whole contract.

    `N` is the part's function names and `S` the subclass itself: `device` types `interface=` by
    one and returns the other.

    Does not add behaviour: its subclass only declares functions and pins.
    """

    def __accepts__(self, name: N) -> None:
        """Use `N` contravariantly, so the checker rejects a name outside the part's functions."""


def _one_maker(design: Design, mpn: str) -> None:
    """Raise when `mpn` is made by more than one manufacturer in the catalogue."""
    parts = design._engine._design._catalogue.by_mpn.get(mpn, ())
    if len(parts) > 1:
        makers = ", ".join(sorted(part.manufacturer for part in parts))
        msg = (
            f"MPN {mpn!r} is ambiguous across manufacturers ({makers}); "
            "the engineer API takes one part per MPN"
        )
        raise AuthorError(msg)


def _check_tag(tag: str | None, name: str | None) -> None:
    if tag is not None:
        bare(tag, "device")
    elif name is None:
        msg = "give a tag, or name= for a device with no tag"
        raise AuthorError(msg)


def part_mpn(part: str | type[Device]) -> str:
    """The MPN a `part` argument stands for: a string, or a part class's `mpn`."""
    if isinstance(part, str):
        return part
    mpn = getattr(part, "mpn", None)
    if not (isinstance(part, type) and issubclass(part, Device) and isinstance(mpn, str)):
        msg = f"part must be an MPN string or a part class with an mpn, not {part!r}"
        raise AuthorError(msg)
    return mpn


def _named(item: Item | Terminal, what: str, *, spec: bool | tuple[str, ...]) -> list[Any]:
    """The functions of `item` that `spec` names: `True` is every one, a tuple the named ones."""
    if spec is False or spec == ():
        return []
    functions = item.functions if isinstance(item, Item) else (item.function,)
    if spec is True:
        return list(functions)
    have = {f.name: f for f in functions}
    for name in spec:
        if name not in have:
            names = ", ".join(sorted(have))
            msg = f"{what}= names {name!r}, which the part lacks; functions: {names}"
            raise AuthorError(msg)
    return [have[name] for name in spec]


def _mark_boundary(
    design: Design,
    item: Item | Terminal,
    *,
    interface: bool | tuple[str, ...],
    unused: bool | tuple[str, ...],
) -> None:
    """Mark the named functions of `item` boundaries; `unused` ones are left open on purpose too."""
    quiet = _named(item, "unused", spec=unused)
    for fn in dict.fromkeys([*_named(item, "interface", spec=interface), *quiet]):
        design._engine.boundary(fn)
    for fn in quiet:
        design._engine.unused(fn)


def _parent_handle(
    design: "Design", parent: "Device | TerminalStrip | None"
) -> Item | Strip | None:
    """The handle `parent=` nests under: a device's item, a strip, or a refusal."""
    if parent is None:
        return None
    return parent._item if isinstance(parent, Device) else parent_item(design, parent)


class Devices:
    """The `device` call of `Design`."""

    @overload
    def device[N: str, S](
        self: "Design",
        tag: str | None,
        part: type[TypedDevice[N, S]],
        *,
        place: str | EllipsisType | None = ...,
        parent: "Device | TerminalStrip | None" = None,
        name: str | None = None,
        interface: bool | tuple[N, ...] = False,
        unused: bool | tuple[N, ...] = False,
        mounted_on: Device | Fn | None = None,
        joins: Mapping[str | int, Pin] | None = None,
        description: str = "",
        position: int | None = None,
        installed: bool = True,
        external: bool = False,
        contacts: str | Mapping[str, str] | None = None,
    ) -> S: ...
    @overload
    def device[D: Device](
        self: "Design",
        tag: str | None,
        part: type[D],
        *,
        place: str | EllipsisType | None = ...,
        parent: "Device | TerminalStrip | None" = None,
        name: str | None = None,
        interface: bool = False,
        unused: bool = False,
        mounted_on: Device | Fn | None = None,
        joins: Mapping[str | int, Pin] | None = None,
        description: str = "",
        position: int | None = None,
        installed: bool = True,
        external: bool = False,
        contacts: str | Mapping[str, str] | None = None,
    ) -> D: ...
    @overload
    def device(
        self: "Design",
        tag: str | None,
        part: str,
        *,
        place: str | EllipsisType | None = ...,
        parent: "Device | TerminalStrip | None" = None,
        name: str | None = None,
        interface: bool | tuple[str, ...] = False,
        unused: bool | tuple[str, ...] = False,
        mounted_on: Device | Fn | None = None,
        joins: Mapping[str | int, Pin] | None = None,
        description: str = "",
        position: int | None = None,
        installed: bool = True,
        external: bool = False,
        contacts: str | Mapping[str, str] | None = None,
    ) -> Any: ...  # noqa: ANN401 -- the string-MPN path is untyped by design (EA4)
    def device(  # noqa: PLR0913 -- the call's own spec signature (EA4)
        self: "Design",
        tag: str | None,
        part: str | type[Device],
        *,
        place: str | EllipsisType | None = ...,
        parent: "Device | TerminalStrip | None" = None,
        name: str | None = None,
        interface: bool | tuple[str, ...] = False,
        unused: bool | tuple[str, ...] = False,
        mounted_on: Device | Fn | None = None,
        joins: Mapping[str | int, Pin] | None = None,
        description: str = "",
        position: int | None = None,
        installed: bool = True,
        external: bool = False,
        contacts: str | Mapping[str, str] | None = None,
    ) -> Any:
        """Add device `tag` (printed `-tag`) of `part`, a part class or an MPN string.

        Does not take a prefixed tag or mount by name. `interface`, `unused`: `True` or names.
        """
        mpn = part_mpn(part)
        _one_maker(self, mpn)
        _check_tag(tag, name)
        _contacts.validate(self, mpn, contacts)
        holder = _parent_handle(self, parent)
        key = self._claim(name or tag or "", per_function=True)
        item = self._engine.item(
            mpn,
            name=key,
            tag=tag,
            at=self._place_node(self._place if place is ... else place),
            group=self._group,
            parent=holder,
            position=position,
            description=description,
            installed=installed,
            external=external,
        )
        _mark_boundary(self, item, interface=interface, unused=unused)
        _contacts.fit(self, item, contacts)
        cls = part if isinstance(part, type) else Device
        made = cls(name or tag or "", item, self._engine)
        if mounted_on is not None:
            mount(self, made, mounted_on)
        fit_leads(self, made, parent, joins)
        return made
