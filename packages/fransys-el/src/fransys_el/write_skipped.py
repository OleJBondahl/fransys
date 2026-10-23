"""One finding per thing the builder left out of the problem (`Skipped`, model-0314, el-0003)."""

from typing import TYPE_CHECKING, cast

from fransys_model.derive import (
    function_designation,
    function_item,
    item_designation,
    port_designation,
    strip_of,
)
from fransys_model.kernel import Finding, SchemaError, Severity, render_id
from fransys_model.vocab import FINDING_CODES

from .codes import FINDING_CODES as LAYOUT_CODES
from .placement_kit import refuse
from .placement_skips import (
    FUNCTION_UNWIRED,
    FUNCTION_WITHOUT_SYMBOL,
    NET_UNDER_TWO_DRAWN_PINS,
    NOT_SERIES_PARALLEL,
    SPARE_FUNCTION,
    SPARE_TERMINAL,
)
from .write_ids import id_texts, port_values

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function, Port

    from .placement_skips import Skipped

__all__ = ["skipped_findings"]

_INFO = {info.code: info for info in (*FINDING_CODES, *LAYOUT_CODES)}


def _name(model: Model, subject: Id[Function]) -> str:
    return function_designation(model, subject)


def _function(model: Model, found: Skipped, subject: Id[Function]) -> Finding:
    name = _name(model, subject)
    return Finding(
        code="FUNCTION_NOT_DRAWN",
        severity=Severity.WARNING,
        subjects=(subject,),
        message=f"function {name} is left out of the drawing ({found.reason}): it has no symbol",
        fix=_INFO["FUNCTION_NOT_DRAWN"].filled(),
    )


def _unwired(model: Model, subject: Id[Function]) -> Finding:
    try:
        name = _name(model, subject)
    except SchemaError:  # a function whose item has no designation is named by its id
        name = render_id(subject)
    return Finding(
        code="FUNCTION_NOT_WIRED",
        severity=Severity.WARNING,
        subjects=(subject,),
        message=f"function {name} has no wired pin, so it is left off the page",
        fix=_INFO["FUNCTION_NOT_WIRED"].filled(),
    )


def _net(model: Model, found: Skipped, subject: Id[Port]) -> Finding:
    name = port_designation(model, subject)
    return Finding(
        code="NET_NOT_DRAWN",
        severity=Severity.WARNING,
        subjects=(subject,),
        message=f"the net of port {name} is left out of the drawing ({found.reason})",
        fix=_INFO["NET_NOT_DRAWN"].filled(),
    )


def _spare(model: Model, subjects: list[Id[object]]) -> Finding:
    """One finding for every spare terminal of the document: the count and the strips (R356)."""
    found = (strip_of(model, function_item(model, cast("Id[Function]", f))) for f in subjects)
    strips = dict.fromkeys(item_designation(model, s) for s in found if s is not None)
    return Finding(
        code="SPARE_TERMINALS",
        severity=Severity.INFO,
        subjects=tuple(subjects),
        message=f"{len(subjects)} spare terminals are in the terminal list, not drawn: strips "
        + ", ".join(strips),
        fix=_INFO["SPARE_TERMINALS"].filled(),
    )


def _spare_functions(model: Model, subjects: list[Id[object]]) -> Finding:
    """One finding for every spare function of the document: the count and the items (R364)."""
    found = (function_item(model, cast("Id[Function]", f)) for f in subjects)
    items = dict.fromkeys(item_designation(model, i) for i in found)
    return Finding(
        code="SPARE_FUNCTIONS",
        severity=Severity.INFO,
        subjects=tuple(subjects),
        message=f"{len(subjects)} spare functions are left off the page: items " + ", ".join(items),
        fix=_INFO["SPARE_FUNCTIONS"].filled(),
    )


def _known(ids: Iterable[str], functions: Mapping[str, Id[object]]) -> bool:
    return all(i in functions for i in ids)


def _bridge(model: Model, subjects: Sequence[Id[object]]) -> Finding:
    names = ", ".join(function_designation(model, cast("Id[Function]", s)) for s in subjects)
    return Finding(
        code="NOT_SERIES_PARALLEL",
        severity=Severity.WARNING,
        subjects=tuple(subjects),
        message=f"the wiring of {names} is a bridge, not series and parallel parts",
        fix=_INFO["NOT_SERIES_PARALLEL"].filled(),
    )


def _finding(
    model: Model, found: Skipped, functions: dict[str, Id[object]], ports: dict[str, Id[object]]
) -> Finding:
    """The finding of one `Skipped` that is not a spare; an unknown reason or id is refused."""
    if found.reason == FUNCTION_WITHOUT_SYMBOL and found.id in functions:
        return _function(model, found, cast("Id[Function]", functions[found.id]))
    if found.reason == FUNCTION_UNWIRED and found.id in functions:
        return _unwired(model, cast("Id[Function]", functions[found.id]))
    if found.reason == NET_UNDER_TWO_DRAWN_PINS and found.id in ports:
        return _net(model, found, cast("Id[Port]", ports[found.id]))
    if found.reason == NOT_SERIES_PARALLEL and _known((found.id, *found.more), functions):
        return _bridge(model, [functions[i] for i in (found.id, *found.more)])
    return refuse(f"skipped {found.what} {found.id}", "pass the Skipped that fransys_el.build gave")


def skipped_findings(model: Model, skipped: Iterable[Skipped]) -> tuple[Finding, ...]:
    """The finding of each `Skipped`, in order; the two spare findings come last."""
    functions, ports = id_texts(model), port_values(model)
    spare: dict[str, list[Id[object]]] = {SPARE_TERMINAL: [], SPARE_FUNCTION: []}
    out = []
    for found in skipped:
        if found.reason in spare and found.id in functions:
            spare[found.reason].append(functions[found.id])
        else:
            out.append(_finding(model, found, functions, ports))
    tail = ((_spare, spare[SPARE_TERMINAL]), (_spare_functions, spare[SPARE_FUNCTION]))
    return (*out, *(make(model, ids) for make, ids in tail if ids))
