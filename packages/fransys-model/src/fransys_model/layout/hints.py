"""Authored layout kinds: soft hints (design/layout-namespace.md, decision 0010).

No kind here has a coordinate or a page-number field, and none ever will: an author
never pins a position. `tests/layout/test_authored_kinds.py` enforces it.
"""

from fransys_model.kernel import AuthoringKey, Id, SchemaError, Value, record
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.core import Function
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.templates import FunctionTemplate, Part

from .order import holder_of


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
        chosen = sum(selector is not None for selector in (self.function, self.template, self.part, self.kind))
        if chosen != 1:
            msg = f"a symbol choice selects by exactly one of function, template, part and kind, not {chosen}"
            raise SchemaError(msg, kind="layout.symbol_choice", record_id=holder_of(self))


@record(kind="layout.pole_group")
class PoleGroup:
    """Draw these one-pole contacts of one device as one multi-pole symbol (`d.poles`).

    `functions` is the pole order the author gave, pole 1 first; a function is listed once.
    With `selector`, the throws of a changeover group face the line (author-0046, layout-0227).
    """

    id: Id[PoleGroup]
    key: AuthoringKey
    functions: tuple[Id[Function], ...]
    selector: bool = False
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Refuse an empty group and a function listed twice; the order is kept."""
        functions = self.functions
        if type(functions) is not tuple or not all(type(one) is Id for one in functions):
            return
        if not functions or len(set(functions)) != len(functions):
            msg = "a pole group lists one function or more, each once"
            raise SchemaError(msg, kind="layout.pole_group", record_id=holder_of(self))
