"""The values the `references` package decides with (layout-0090, S1): no rule lives here."""

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from fransys_layout.stages.offstubs import OffEnd, PortText
    from fransys_layout.stages.stacking import JoinedRun, PageStack, StackedPort
    from fransys_layout.stages.terminal_rows import TerminalChains
    from fransys_layout.stages.types import (
        Column,
        Connection,
        DrawnFunction,
        FunctionSpec,
        Handle,
        LinkDecision,
        MarkerSide,
        NetGroup,
        PagePlan,
        PortRef,
        PowerEnd,
        Profile,
        RailEnd,
        SheetFormat,
        StubText,
    )
    from fransys_model.kernel import AuthoringKey, Finding, Id

    from .digits import SetDigits

# `(drawing_set, page)`: pages are ordered by this pair throughout the package.
type Page = tuple[int, int]

# A location's root-to-leaf path: each node's handle paired with its own label, root first
# (units spec U7), mirroring `fransys_model.derive.drawing_text.LocationPath`. Fed straight
# to `location_prefix`, whose common-ancestor walk compares the handle half, never the label.
type LocationPath = tuple[tuple[Handle, str], ...]


class Seated(Protocol):
    """A function's seat on a page: the column it stands in there (a placement is one)."""

    @property
    def function(self) -> Id[Any]:
        """The function seated."""
        ...

    @property
    def drawing_set(self) -> int:
        """The drawing set of its page."""
        ...

    @property
    def page(self) -> int:
        """Its page in that set."""
        ...

    @property
    def column(self) -> AuthoringKey:
        """The column it stands in on that page."""
        ...


@dataclass(frozen=True, slots=True)
class PortEnd:
    """One end of a cut or of a text: a port on a page (S9: a decision holds no coordinate)."""

    ref: PortRef
    page: Page


@dataclass(frozen=True, slots=True)
class Cut:
    """One cut: a conductor or a net group's step between two pages, `ends` in port order."""

    connection: Handle
    physical_net: Handle
    ends: tuple[PortEnd, PortEnd]


@dataclass(frozen=True, slots=True)
class LinkWorld:
    """What the cuts are read from: each function's column by page, and its drawing."""

    where: dict[Handle, dict[Page, AuthoringKey]]
    drawn_of: dict[Handle, DrawnFunction]


class Leave(Enum):
    """S9: which of its function's ports a text stands at (C22 `FREE`, C17 `NORTH`/`SOUTH`)."""

    PORT = "port"
    FREE = "free"
    FREE_OR_PORT = "free_or_port"
    NORTH = "north"
    SOUTH = "south"


@dataclass(frozen=True, slots=True, kw_only=True)
class MarkerDecision:
    """S9: one reference or stub text as `references` decides it; `texts` builds its marker."""

    connection: Id[Any]
    function: Id[Any]
    port: Id[Any]
    side: MarkerSide
    drawing_set: int
    page: int
    star: str = ""
    lines: int = 1
    size: tuple[int, int]
    partner: Id[Any]
    partner_set: int
    partner_page: int
    leave: Leave = Leave.PORT
    partner_leave: Leave = Leave.PORT
    out: int = 0
    text: str = ""
    end_text: StubText | None = None
    merge: StubText | None = None
    run: int | None = None
    # D5: a power end's symbol key and printed text, `""` for an ordinary end; it keeps its cut
    symbol: str = ""
    symbol_text: str = ""


@dataclass(frozen=True, slots=True)
class Beside:
    """S12, layout-0070: where two ports are wired beside each other, per drawing set."""

    pairs: Mapping[tuple[Id[Any], Id[Any]], frozenset[int]]
    sets: Mapping[Id[Any], frozenset[int]]


@dataclass(frozen=True, slots=True)
class Joins:
    """S12: the joins decided on `place`'s own stacking (`joins.joined_runs`), before `place`."""

    beside: Beside
    runs: tuple[JoinedRun, ...]
    findings: tuple[Finding, ...]


@dataclass(frozen=True, slots=True)
class Star:
    """One net drawn as markers: its counted ports, its reference and the conductors it drops."""

    ports: tuple[PortRef, ...]
    ref: PortRef
    conductors: frozenset[Id[Any]]
    by_designation: bool
    # C3: port -> the first port of its cluster (ports joined by a kept neighbour wire in any set)
    cluster: tuple[tuple[Id[Any], Id[Any]], ...] = ()
    # layout-0070: the same per drawing set, `(set, port, first)` for a port that is not its
    # cluster's first there; a port missing from a set is the first of a cluster of its own
    set_cluster: tuple[tuple[int, Id[Any], Id[Any]], ...] = ()
    # every wire handle of the net: the markers' connection when no conductor is dropped
    wires: frozenset[Id[Any]] = frozenset()
    # layout-0080: `(port, drawing_set)` at a unit's boundary that take no marker (`exempt`)
    exempt: frozenset[tuple[Id[Any], int]] = frozenset()


@dataclass(frozen=True, slots=True)
class MarkerScene:
    """What every star, split and off stub text is decided against: the seats and the sheet."""

    seats: tuple[Seated, ...]
    drawn: tuple[DrawnFunction, ...]
    sheet: SheetFormat
    profile: Profile
    digits: Mapping[int, tuple[int, int]] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True, slots=True)
class MarkerSpec:
    """One star text to decide: the conductor it stands for, its two ends, its line count."""

    connection: Id[Any]
    end: tuple[PortEnd, Leave]
    partner: tuple[PortEnd, Leave]
    lines: int
    kind: str
    side: MarkerSide


@dataclass(frozen=True, slots=True)
class BlackBoxReads:
    """What `black_box_sets` reads of the model, built by `read/units.py`."""

    nested: frozenset[Id[Any] | None]
    edges: frozenset[Id[Any]]
    top: Callable[[Id[Any] | None], Id[Any] | None]


@dataclass(frozen=True, slots=True)
class OffInputs:
    """What `with_off_markers` takes of the inputs: the page, the crossing conductors, texts."""

    sheet: SheetFormat
    profile: Profile
    crossing: tuple[Connection, ...]
    off_texts: tuple[PortText, ...]
    outward: Mapping[Id[Any], frozenset[int]]


@dataclass(frozen=True, slots=True)
class OffStubs:
    """What `_off_markers` draws stubs for, and what its ports already carry (S14, D10)."""

    crossing: tuple[Connection, ...]
    off_texts: Mapping[Id[Any], Sequence[StubText]]
    away: frozenset[AuthoringKey | tuple[Id[Any], AuthoringKey]] = frozenset()
    outward: Mapping[Id[Any], frozenset[int]] = field(default_factory=lambda: MappingProxyType({}))
    busy: Mapping[tuple[Id[Any], int, int], int] = field(
        default_factory=lambda: MappingProxyType({})
    )
    refs: Mapping[tuple[Id[Any], int, int], MarkerDecision] = field(
        default_factory=lambda: MappingProxyType({})
    )
    stands: Mapping[tuple[Id[Any], Page], StackedPort] = field(
        default_factory=lambda: MappingProxyType({})
    )
    order: Mapping[Page, tuple[AuthoringKey, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )


@dataclass(frozen=True, slots=True)
class Seat:
    """S10: a function in a planned column on a planned page, before `place` gives it a place."""

    function: Id[Any]
    drawing_set: int
    page: int
    column: AuthoringKey


@dataclass(frozen=True, slots=True)
class Seating:
    """S10: the pages as `plan_pages` planned them and `place` stacks them, before any is placed."""

    plans: tuple[PagePlan, ...]
    columns: tuple[Column, ...]
    drawn: tuple[DrawnFunction, ...]
    seats: tuple[Seat, ...]
    stacks: Mapping[Page, PageStack]


@dataclass(frozen=True, slots=True, kw_only=True)
class ReferenceInputs:
    """What `references` decides from: the run's nets, its planned pages and what was read."""

    sheet: SheetFormat
    profile: Profile
    connections: tuple[Connection, ...]
    net_groups: tuple[NetGroup, ...]
    functions: tuple[FunctionSpec, ...]
    seating: Seating
    replicas: frozenset[AuthoringKey]
    location_paths: Mapping[int, LocationPath]
    exempt: frozenset[tuple[Id[Any], int]]
    crossing: tuple[Connection, ...]
    off_texts: tuple[PortText, ...]
    off_ends: tuple[OffEnd, ...]
    outward: Mapping[Id[Any], frozenset[int]]
    chains: TerminalChains
    # D5: each port on a power net, read; an end there takes the symbol, not a reference
    power: Mapping[Id[Any], PowerEnd] = MappingProxyType({})
    # V3: each drawn pin end of a rail wire (not drawn); the pin takes a symbol marker
    rail_ends: tuple[RailEnd, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class References:
    """S9: every decision of D1's step 4, one frozen value; `place` and `texts` take it whole."""

    joins: tuple[JoinedRun, ...]
    decisions: tuple[LinkDecision, ...]
    markers: tuple[MarkerDecision, ...]
    off_ends: tuple[OffEnd, ...]
    digits: tuple[SetDigits, ...]
    echoes: tuple[Cut, ...]
    connections: tuple[Connection, ...]
    net_groups: tuple[NetGroup, ...]

    @property
    def power(self) -> tuple[MarkerDecision, ...]:
        """The markers that are power ends (`symbol` set), in `markers` order."""
        return tuple(one for one in self.markers if one.symbol)
