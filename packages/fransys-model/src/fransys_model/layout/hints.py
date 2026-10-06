"""Authored layout kinds: soft hints (design/layout-namespace.md, decision 0010).

No kind here has a coordinate or a page-number field, and none ever will: an author
never pins a position. `tests/layout/test_authored_kinds.py` enforces it.
"""

from fransys_model.kernel import AuthoringKey, Id, SchemaError, Value, record, value
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.core import Function
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.templates import FunctionTemplate, Part

from .order import by_index, holder_of


@value
class ChainEntry:
    """One function of a `Chain` and its place in the series; `index` is the order."""

    function: Id[Function]
    index: int


@record(kind="layout.chain")
class Chain:
    """One series chain of functions, source first: what a rung lowers to beside connectivity.

    Example: the invented pump starter has breaker, contactor main contact, overload
    and motor functions with `index` 0 to 3. The order is the explicit `index`, never
    the tuple position; `entries` is stored sorted by `index`. A chain states intent
    only: whether consecutive functions really are connected is the layout engine's
    check, because it needs net closure.
    """

    id: Id[Chain]
    key: AuthoringKey
    entries: tuple[ChainEntry, ...]
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Store `entries` in `index` order; a repeated `index` or `function` is refused."""
        holder = holder_of(self)
        entries = by_index(self.entries, ChainEntry, kind="layout.chain", holder=holder)
        if entries is None:
            return
        functions = [entry.function for entry in entries]
        if all(type(function) is Id for function in functions) and len(set(functions)) != len(
            functions
        ):
            msg = "a function appears twice in one chain"
            raise SchemaError(msg, kind="layout.chain", record_id=holder)
        object.__setattr__(self, "entries", entries)


@record(kind="layout.group_hint", subject="function", unique=True)
class GroupHint:
    """Draw this function with that `=` group, whatever the placement of its item says.

    Example: the e-stop permissive contact that gates the pump contactor is placed
    under `=SAFETY` and hinted into `=PUMP1`. At most one per function.
    """

    id: Id[GroupHint]
    key: AuthoringKey
    function: Id[Function]
    group: Id[AspectNode]
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.keep_together")
class KeepTogether:
    """Put these `=` groups on one page when they fit; `groups` is a set, sorted by id."""

    id: Id[KeepTogether]
    key: AuthoringKey
    groups: tuple[Id[AspectNode], ...]
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Store `groups` in id order; a group listed twice is refused."""
        groups = self.groups
        if type(groups) is not tuple or not all(type(group) is Id for group in groups):
            return
        if len(set(groups)) != len(groups):
            msg = "a group is listed twice"
            raise SchemaError(msg, kind="layout.keep_together", record_id=holder_of(self))
        object.__setattr__(self, "groups", tuple(sorted(groups)))


@record(kind="layout.break_before", subject="group", unique=True)
class BreakBefore:
    """Start a new page before this `=` group. At most one per group."""

    id: Id[BreakBefore]
    key: AuthoringKey
    group: Id[AspectNode]
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.order_hint")
class OrderHint:
    """Draw group `before` ahead of group `after`, overriding the profile convention.

    Hints that contradict each other across records are the layout engine's
    `HintError`, not a model rule.
    """

    id: Id[OrderHint]
    key: AuthoringKey
    before: Id[AspectNode]
    after: Id[AspectNode]
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Refuse a group ordered before itself."""
        ids = type(self.before) is Id and type(self.after) is Id
        if ids and self.before == self.after:
            msg = "a group cannot be drawn before itself"
            raise SchemaError(msg, kind="layout.order_hint", record_id=holder_of(self))


@record(kind="layout.symbol_choice")
class SymbolChoice:
    """Which library symbol draws a function, a function template, a part or a kind.

    Exactly one of `function`, `template`, `part`, `kind` is set; the most specific
    choice wins in the engine, in that order (`function` beats `template` beats `part`
    beats `kind`). A choice naming `part` means every function of that part, which
    cannot tell one function of a part from another (a relay's coil from its
    contacts); `template` names one `FunctionTemplate`, so every instance of that
    function across every item of the part gets the choice. `symbol` is a
    symbol-library slug (`"make-contact"`). `port_map` maps a model port name to the
    symbol port name where they differ (`"13"` to `"1.in"`); a port not listed keeps
    its name.
    """

    id: Id[SymbolChoice]
    key: AuthoringKey
    function: Id[Function] | None
    template: Id[FunctionTemplate] | None
    part: Id[Part] | None
    kind: FunctionKind | None
    symbol: str
    port_map: frozendict[str, str] = frozendict()
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Refuse a choice that selects by none of function/template/part/kind, or several."""
        chosen = sum(
            selector is not None
            for selector in (self.function, self.template, self.part, self.kind)
        )
        if chosen != 1:
            msg = (
                "a symbol choice selects by exactly one of function, template, part and "
                f"kind, not {chosen}"
            )
            raise SchemaError(msg, kind="layout.symbol_choice", record_id=holder_of(self))
