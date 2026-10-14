"""The terminal-copy ratchet of decision layout-0214.

A loose copy is a terminal symbol on a page that no wire, link marker or power symbol of that
page meets, and that stands for one of four causes: the terminal has no wire; its far ends are
drawn on other pages of the page's drawing set and none on this one; a unit's terminal is
drawn in a box cell of another unit, with every wire inside its own unit; or its far ends stand
only in other drawing sets (a unit's black box in its parent's set whose wire is a stub at the
unit's own page). Jumper routes do not meet. The count over the models below may only be zero.
The pump-station example lives in another repository, so these fixtures stand for it.
"""

import importlib.util
import sys
import tempfile
from collections import defaultdict
from functools import cache
from pathlib import Path
from typing import Any

import fransys as fr
from fransys_el import OPTIONS

from fransys_layout.engines import lay_out_schematic
from fransys_model.derive.indexes import build_indexes
from fransys_model.kernel import freeze
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    Page,
    PowerSymbol,
    Route,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.enums import ConductorKind, FunctionKind
from fransys_model.vocab.membership import in_unit_subtree
from fransys_model.vocab.tables import conductors, functions, items, ports

ROOT = Path(__file__).resolve().parent.parent
LAYOUT_TESTS = ROOT / "packages" / "fransys-layout" / "tests"
FIELD_CASES = ROOT / "tests" / "field_cases"


def _load(path: Path, name: str, extra: Path | None = None) -> Any:
    sys.path.insert(0, str(extra or path.parent))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(extra or path.parent))
    return module


def _field_unit(module: Any, attr: str, subject: str) -> Any:
    """The model a field case's test builds: its unit at U1 under a cabinet document."""
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text(f"# {subject.capitalize()}\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(getattr(module, attr), "U1")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, subject, cover=cover)).model


@cache
def _models() -> dict[str, Any]:
    cabinet = _load(LAYOUT_TESTS / "layout_cabinet.py", "layout_cabinet_for_copies")
    strip = _load(
        FIELD_CASES / "test_a_terminal_wired_only_from_another_block_is_drawn_there_alone.py",
        "strip_case_for_copies",
    )
    bank = _load(
        FIELD_CASES / "test_a_larger_module_only_adds_pages_to_a_bank_of_relays.py",
        "bank_case_for_copies",
    )
    boundary = _load(
        ROOT / "tests" / "test_dd_boundary_terminal_crash.py", "boundary_crash_for_copies"
    )
    power = _load(
        FIELD_CASES / "test_a_power_text_does_not_seal_a_wire_in.py", "power_text_for_copies"
    )
    return {
        "cabinet": lay_out_schematic(freeze(cabinet.build_cabinet()), OPTIONS)[0],
        "cabinet-discovery": lay_out_schematic(
            freeze(cabinet.build_cabinet(discovery=True)), OPTIONS
        )[0],
        "strip-block": strip.built().result.model,
        "bank-of-relays": bank._built(None, 8).model,
        "boundary-stub": boundary._build((("K1", "A1"),)),
        "power-text": _field_unit(power, "_shape", "shape"),
    }


def _met(model: Any) -> dict[Any, set[Any]]:
    """Per page, the ports a non-jumper route, link marker or power symbol ends at."""
    kinds = conductors(model)
    wired: dict[Any, set[Any]] = defaultdict(set)
    for route in layout_of(model, Route).values():
        if route.conductor is None or kinds[route.conductor].kind is not ConductorKind.JUMPER:
            wired[route.page].update((route.a, route.b))
    for marker in layout_of(model, LinkMarker).values():
        wired[marker.page].add(marker.port)
    for power in layout_of(model, PowerSymbol).values():
        wired[power.page].add(power.port)
    return wired


def _far_ends(model: Any, function: Any) -> list[tuple[Any, Any]]:
    """Each non-jumper conductor of `function` as (far port, far function)."""
    ix = build_indexes(model)
    kinds, port_records = conductors(model), ports(model)
    found = []
    for port in ix.ports_by_function.get(function, ()):
        for c in ix.conductors_by_port.get(port, ()):
            record = kinds[c]
            if record.kind is not ConductorKind.JUMPER:
                far = record.b if record.a == port else record.a
                found.append((far, port_records[far].function))
    return found


def _no_wire(model: Any, function: Any) -> bool:
    ix = build_indexes(model)
    own = ix.ports_by_function.get(function, ())
    return not _far_ends(model, function) and not any(ix.nets_by_port.get(p) for p in own)


def _block_shape(model: Any, function: Any, page: Any, placed: dict[Any, set[Any]]) -> bool:
    """No far end on `page`, and one on another page of its drawing set."""
    pages = layout_of(model, Page)
    there = set()
    for far_port, far in _far_ends(model, function):
        there |= placed.get(far, set()) | placed.get(far_port, set())
    return page not in there and any(pages[q].drawing_set == pages[page].drawing_set for q in there)


def _unwired_box_cell(model: Any, function: Any, page: Any) -> bool:
    sets = layout_of(model, DrawingSet)
    unit = items(model)[functions(model)[function].item].unit
    here = sets[layout_of(model, Page)[page].drawing_set].unit
    if unit is None or here == unit:
        return False
    far_items = (functions(model)[far].item for _, far in _far_ends(model, function))
    return not any(not in_unit_subtree(model, i, unit) for i in far_items)


def _other_set(model: Any, function: Any, page: Any, placed: dict[Any, set[Any]]) -> bool:
    """Its far ends stand only in other drawing sets: none in the page's set."""
    pages = layout_of(model, Page)
    there = set()
    for far_port, far in _far_ends(model, function):
        there |= placed.get(far, set()) | placed.get(far_port, set())
    here = pages[page].drawing_set
    return bool(there) and not any(pages[q].drawing_set == here for q in there)


def loose_copies(model: Any) -> list[tuple]:
    """Each `(page, function)` terminal copy no wire meets there, for one of the four causes."""
    wired = _met(model)
    ports_of = build_indexes(model).ports_by_function
    placed: dict[Any, set[Any]] = defaultdict(set)
    for p in layout_of(model, SymbolPlacement).values():
        placed[p.function].add(p.page)
    found = []
    for p in layout_of(model, SymbolPlacement).values():
        record = functions(model).get(p.function)
        if record is None or record.kind is not FunctionKind.TERMINAL:
            continue
        if set(ports_of.get(p.function, ())) & wired[p.page]:
            continue
        if (
            _no_wire(model, p.function)
            or _block_shape(model, p.function, p.page, placed)
            or _unwired_box_cell(model, p.function, p.page)
            or _other_set(model, p.function, p.page, placed)
        ):
            found.append((p.page, p.function))
    return found


def _terminal_placements(model: Any) -> int:
    kinds = functions(model)
    return sum(
        1
        for p in layout_of(model, SymbolPlacement).values()
        if p.function in kinds and kinds[p.function].kind is FunctionKind.TERMINAL
    )


def test_the_models_lay_out_terminals() -> None:
    assert all(_terminal_placements(m) > 0 for m in _models().values())


def test_no_terminal_copy_stands_where_no_wire_meets_it() -> None:
    counts = {name: len(loose_copies(m)) for name, m in _models().items()}
    assert sum(counts.values()) == 0, counts


def _terminal_references(model: Any) -> int:
    """Link markers at a non-terminal port whose partner marker sits at a terminal port."""
    markers = layout_of(model, LinkMarker)
    kinds, port_records = functions(model), ports(model)
    count = 0
    for marker in markers.values():
        partner = markers.get(marker.partner)
        if partner is None:
            continue
        near, far = port_records[marker.port].function, port_records[partner.port].function
        if (
            kinds[near].kind is not FunctionKind.TERMINAL
            and kinds[far].kind is FunctionKind.TERMINAL
        ):
            count += 1
    return count


def test_a_terminal_fanned_out_to_groups_on_one_page_draws_no_reference() -> None:
    """The power-text model's X1:5 feeds four lamps on one page: its home joins them."""
    assert _terminal_references(_models()["power-text"]) == 0
