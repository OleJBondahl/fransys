"""Vocabulary: instance-level kinds (design/vocabulary.md 6, "Instance level")."""

from fransys_model.kernel import AuthoringKey, Id, Value, record

from .enums import FunctionKind, PortRole
from .release_version import refuse_below_one
from .templates import FunctionTemplate, Part, PortTemplate


@record(kind="unit_release")
class UnitRelease:
    """A released, independently-built component: a product as a part is.

    Example: `UnitRelease(name="demo-io-board", version=1, revision=3, interface="7",
    title="Relay interface board", number="SKX-RIB-2")` is one record however many `Unit`s
    instantiate it; its instances are placements, as items are. Its key is `("unit_release",
    name, str(version), str(revision))`, so two releases that differ in another field conflict.
    `version` and `revision` are ints of 1 or more (`release_version`), printed as
    `derive.revision_text` (`1.3`). `interface` is the boundary's version, bumped by hand and
    checked at release against every other revision of the name (`INTERFACE_NOT_BUMPED`).
    `title` and `number` are the unit's own; `class_code` is the letter its floating instances
    number from (`U`); all default to `""`. Read through `derive.unit_release`.
    """

    id: Id[UnitRelease]
    key: AuthoringKey
    name: str
    version: int
    revision: int
    interface: str
    title: str = ""
    number: str = ""
    class_code: str = ""
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Refuse a `version` or `revision` below 1; other types are `freeze()`'s."""
        what = f"unit release {self.name!r}"
        refuse_below_one("unit_release", self.id, what, "version", self.version)
        refuse_below_one("unit_release", self.id, what, "revision", self.revision)


@record(kind="unit")
class Unit:
    """One instance of a released, independently-built component.

    Example: `io_board` instantiates one `Unit` per call, all pointing at the one
    `UnitRelease` for `demo-io-board`, so a cabinet holding two boards has two `Unit`
    records and one release. `release` carries the name, version, revision, interface,
    title and number. `parent` is the unit this instance sits in; a subtree is the
    unit and every unit whose `parent` chain reaches it. Guarded by `validators.structure`
    (`UNIT_CYCLE`). `release`'s own `interface` is now checked at release
    (`INTERFACE_NOT_BUMPED`). `tag` is the instance's written tag (`U1`),
    `None` to be numbered; `derive.unit_tag` reads the tag.
    """

    id: Id[Unit]
    key: AuthoringKey
    release: Id[UnitRelease]
    parent: Id[Unit] | None
    tag: str | None = None
    ext: frozendict[str, Value] = frozendict()


@record(kind="item")
class Item:
    """One physical thing.

    Example: the invented relay `-K1` example is one `Item` with `part` set to the
    relay `Part`; terminal strip `X03` is an `Item` whose four terminals are child
    `Item`s via `parent`. `position` is the physical order within the parent (PLC
    slot, place on the rail); it is a fact about the build, not a drawing coordinate.
    `tag` is the engineer's authored tag; `tag=None` means "number me". The numbered text
    lives in `facet.assigned_designation`, never here. `installed=False` keeps it in drawings and
    reservations but drops it from the BOM. `unit` is the unit this item belongs to by
    membership, not by key or location; `None` is the integrating
    script's own wiring. `external=True`: someone else supplies and owns it; an item is
    external if it or any parent-chain ancestor is, see `derive.external`. Guarded by
    `part_conformance` (when `part` is set) and `validators.structure` (`CONTAINMENT_CYCLE`).
    """

    id: Id[Item]
    key: AuthoringKey
    part: Id[Part] | None
    parent: Id[Item] | None
    position: int | None
    tag: str | None
    description: str
    installed: bool = True
    unit: Id[Unit] | None = None
    external: bool = False
    ext: frozendict[str, Value] = frozendict()


@record(kind="function")
class Function:
    """One electrical function of one item: the unit Fransys draws as a symbol.

    Example: the relay `-K1` example has a `coil` `Function` drawn on the control
    page and a `co_1` `Function` drawn on the power page; both reference the same
    `item`. Guarded by `part_conformance` when `template` is set.
    """

    id: Id[Function]
    key: AuthoringKey
    item: Id[Item]
    template: Id[FunctionTemplate] | None
    name: str
    kind: FunctionKind
    ext: frozendict[str, Value] = frozendict()


@record(kind="port")
class Port:
    """A connection point on a `Function`.

    Example: the coil `Function` of the relay example has ports `A1` and `A2`.
    Guarded by `part_conformance` when `template` is set. `marking` is the part's own
    pin marking: `None` means "print the port's name", `""`
    means "print nothing", any other string is printed as given.
    """

    id: Id[Port]
    key: AuthoringKey
    function: Id[Function]
    template: Id[PortTemplate] | None
    name: str
    role: PortRole
    marking: str | None = None
    ext: frozendict[str, Value] = frozendict()
