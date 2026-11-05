"""One finding per thing the builder left out of the problem (`Skipped`, model-0314, el-0003)."""

from typing import TYPE_CHECKING, cast

from fransys_model.derive import (
    function_designation,
    function_item,
    has_function,
    item_designation,
    port_designation,
    strip_of,
)
from fransys_model.vocab import FINDING_CODES

from .codes import FINDING_CODES as LAYOUT_CODES
from .kit_keys import function_of
from .placement_kit import refuse
from .placement_nets import net_ports
from .placement_skips import (
    FUNCTION_UNWIRED,
    FUNCTION_WITHOUT_SYMBOL,
    NET_UNDER_TWO_DRAWN_PINS,
    NOT_SERIES_PARALLEL,
    SPARE_FUNCTION,
    SPARE_TERMINAL,
)
from .write_ids import id_texts

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.vocab import Function, Port

    from .placement_skips import Skipped

__all__ = ["skipped_findings"]

_INFO = {info.code: info for info in (*FINDING_CODES, *LAYOUT_CODES)}


def _function(model: Model, found: Skipped, subject: Id[Function]) -> Finding:
    name = function_designation(model, subject)
    return _INFO["FUNCTION_NOT_DRAWN"].finding((subject,), f"function {name} is left out of the drawing ({found.reason}): it has no symbol")


def _unwired(model: Model, subject: Id[Function] | Id[Port]) -> Finding:
    """A boxed connector's pin is skipped by its port (el-0014): the port prints its designation, a function its own (el-0110)."""
    function = cast("Id[Function]", subject)
    name = function_designation(model, function) if has_function(model, function) else port_designation(model, cast("Id[Port]", subject))
    return _INFO["FUNCTION_NOT_WIRED"].finding((subject,), f"function {name} has no wired pin, so it is left off the page")


def _net(model: Model, found: Skipped, subject: Id[Port]) -> Finding:
    name = port_designation(model, subject)
    return _INFO["NET_NOT_DRAWN"].finding((subject,), f"the net of port {name} is left out of the drawing ({found.reason})")


def _spare_finding(code: str, subjects: list[Id[object]], text: str, names: Iterable[str]) -> Finding:
    return _INFO[code].finding(tuple(subjects), f"{len(subjects)} {text} " + ", ".join(dict.fromkeys(names)))


def _spare(model: Model, subjects: list[Id[object]]) -> Finding:
    """One finding for every spare terminal of the document: the count and the strips (R356)."""
    found = (strip_of(model, function_item(model, cast("Id[Function]", f))) for f in subjects)
    strips = (item_designation(model, s) for s in found if s is not None)
    return _spare_finding("SPARE_TERMINALS", subjects, "spare terminals are in the terminal list, not drawn: strips", strips)


def _spare_functions(model: Model, subjects: list[Id[object]]) -> Finding:
    """One finding for every spare function of the document: the count and the items (R364)."""
    found = (function_item(model, function_of(model, cast("Id[Function]", f))) for f in subjects)
    return _spare_finding("SPARE_FUNCTIONS", subjects, "spare functions are left off the page: items", (item_designation(model, i) for i in found))


def _bridge(model: Model, subjects: Sequence[Id[object]]) -> Finding:
    names = ", ".join(function_designation(model, cast("Id[Function]", s)) for s in subjects)
    return _INFO["NOT_SERIES_PARALLEL"].finding(tuple(subjects), f"the wiring of {names} is a bridge, not series and parallel parts")


def _finding(model: Model, found: Skipped, functions: dict[str, Id[object]], ports: Mapping[str, Id[Port]]) -> Finding:
    """The finding of one `Skipped` that is not a spare; an unknown reason or id is refused."""
    if found.reason == FUNCTION_WITHOUT_SYMBOL and found.id in functions:
        return _function(model, found, cast("Id[Function]", functions[found.id]))
    if found.reason == FUNCTION_UNWIRED and found.id in functions:
        return _unwired(model, cast("Id[Function] | Id[Port]", functions[found.id]))
    if found.reason == NET_UNDER_TWO_DRAWN_PINS and found.id in ports:
        return _net(model, found, ports[found.id])
    if found.reason == NOT_SERIES_PARALLEL and all(i in functions for i in (found.id, *found.more)):
        return _bridge(model, [functions[i] for i in (found.id, *found.more)])
    return refuse(f"skipped {found.what} {found.id}", "pass the Skipped that fransys_el.build gave")


def skipped_findings(model: Model, skipped: Iterable[Skipped]) -> tuple[Finding, ...]:
    """The finding of each `Skipped`, in order; the two spare findings come last."""
    functions, ports = id_texts(model), net_ports(model)
    spare: dict[str, list[Id[object]]] = {SPARE_TERMINAL: [], SPARE_FUNCTION: []}
    out = []
    for found in skipped:
        if found.reason in spare and found.id in functions:
            spare[found.reason].append(functions[found.id])
        else:
            out.append(_finding(model, found, functions, ports))
    tail = ((_spare, spare[SPARE_TERMINAL]), (_spare_functions, spare[SPARE_FUNCTION]))
    return (*out, *(make(model, ids) for make, ids in tail if ids))
