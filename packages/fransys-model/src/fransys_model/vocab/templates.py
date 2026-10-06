"""Vocabulary: type-level kinds declared on a `Part` (design/vocabulary.md 6, "Type level"; 7)."""

from typing import TYPE_CHECKING, Any

from fransys_model.kernel import AuthoringKey, Id, SchemaError, Value, record

from .enums import (
    ConductorMark,
    Energy,
    FunctionKind,
    LinkKind,
    LinkRest,
    PartCategory,
    PoleSide,
    PortRole,
    ProtectionType,
)

if TYPE_CHECKING:
    from .connectivity import Conductor, Mate, Net

_POWER_KINDS = frozenset({FunctionKind.SUPPLY, FunctionKind.LOAD})


def _holder(found: Net | Conductor | Mate | InternalLink | FunctionTemplate) -> Id[Any] | None:
    """The id of the record that refuses, for its error; `None` if it is not even an `Id`."""
    return found.id if type(found.id) is Id else None


def _order_ends(found: Conductor | Mate | InternalLink, kind: str, refusal: str) -> None:
    """Store the ends `a` and `b` of `found` in id order; the same end twice is refused.

    Ends that are not `Id`s are left as they are: `freeze()` reports them.
    """
    first, second = found.a, found.b
    if type(first) is not Id or type(second) is not Id:
        return
    if first == second:
        raise SchemaError(refusal, kind=kind, record_id=_holder(found))
    if second < first:
        object.__setattr__(found, "a", second)
        object.__setattr__(found, "b", first)


@record(kind="part_library")
class PartLibrary:
    """A part library and its version: the provenance of the `Part`s it supplied (vocabulary.md).

    Example: `PartLibrary(name="invented-parts", version="1.4.0")` with key
    `("part_library", "invented-parts")`. The name and version live only here; a `Part`
    holds the id. Two libraries of one name with different versions are
    `PART_LIBRARY_VERSION_CONFLICT`.
    """

    id: Id[PartLibrary]
    key: AuthoringKey
    name: str
    version: str
    ext: frozendict[str, Value] = frozendict()


@record(kind="part")
class Part:
    """A catalog type: the only home of an MPN (vocabulary.md 6 and foundations.md 2.1).

    Example: the invented relay example (design/examples.md 11) is one `Part`
    (`class_code="K"`) shared by every `-K1`, `-K2`, ... `Item`, so the MPN is never typed twice.
    Guarded by `part_conformance`, which checks every referencing `Item` matches its templates.
    `library` names the part library that supplied it, `None` for a part authored in
    Python.
    """

    id: Id[Part]
    key: AuthoringKey
    mpn: str
    manufacturer: str
    description: str
    category: PartCategory
    class_code: str
    library: Id[PartLibrary] | None = None
    ext: frozendict[str, Value] = frozendict()


@record(kind="function_template")
class FunctionTemplate:
    """A function every instance of a `Part` has (design/vocabulary.md 6, 7).

    Example: the relay `Part` declares `FunctionTemplate`s `coil`, `no_1`, `co_1`
    (design/examples.md 11); `instantiate` stamps one `Function` per template onto
    each `Item`.
    Guarded by `part_conformance`. `protection_type` is the device type of a protection function
    (decision model-0127; F3): `None` means not declared. `energy` says which way energy flows
    through a `supply` or `load` function (decision model-0131): `None` means the kind's default.
    """

    id: Id[FunctionTemplate]
    key: AuthoringKey
    part: Id[Part]
    name: str
    kind: FunctionKind
    protection_type: ProtectionType | None = None
    energy: Energy | None = None
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Refuse a `protection_type` on a function that is not `kind = protection`."""
        if self.protection_type is not None and self.kind is not FunctionKind.PROTECTION:
            msg = "only a protection function has a protection type"
            raise SchemaError(msg, kind="function_template", record_id=_holder(self))
        if self.energy is not None and self.kind not in _POWER_KINDS:
            msg = "only a supply or load function has an energy direction"
            raise SchemaError(msg, kind="function_template", record_id=_holder(self))


@record(kind="port_template")
class PortTemplate:
    """A pin of a `FunctionTemplate` (design/vocabulary.md 6, 7).

    Example: the relay's `coil` template declares `PortTemplate`s `A1` and `A2`
    (design/examples.md 11). Guarded by `part_conformance`. `marking` is the part's
    own pin marking
    (decision model-0053; F2): `None` means "print the port's name", `""` means "print
    nothing", any other string is printed as given. `pole_side` and `conductor_mark` are the
    pin's facts (decision model-0126; F9): which side of a switching device it is on, and its
    IEC 60445 conductor designation. `None` means not stated. PE stays `role = PE`.
    """

    id: Id[PortTemplate]
    key: AuthoringKey
    function: Id[FunctionTemplate]
    name: str
    role: PortRole
    marking: str | None = None
    pole_side: PoleSide | None = None
    conductor_mark: ConductorMark | None = None
    ext: frozendict[str, Value] = frozendict()


@record(kind="internal_link")
class InternalLink:
    """Connectivity inside a part, between two `PortTemplate`s (vocabulary.md and connectivity.md).

    Example: the relay's `co_1` template links `11`-`14` and `12`-`14` as `SWITCHED`
    (examples.md 11); a fuse part links its two end ports as `CONDUCTIVE`, joining net
    closure. Read by `derive.closure`.
    """

    id: Id[InternalLink]
    key: AuthoringKey
    a: Id[PortTemplate]
    b: Id[PortTemplate]
    kind: LinkKind
    rest: LinkRest | None = None
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Store the ends in id order; refuse one end twice or a `rest` on a link not switched."""
        _order_ends(self, "internal_link", "an internal link joins two different port templates")
        if self.rest is not None and self.kind is not LinkKind.SWITCHED:
            msg = "only a switched internal link has a rest state"
            raise SchemaError(msg, kind="internal_link", record_id=_holder(self))
