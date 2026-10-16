"""The terminal-copy ratchet of decision layout-0214.

A loose copy is a terminal symbol on a page that no wire, link marker or power symbol of that
page meets, and that stands for one of four causes: the terminal has no wire; its far ends are
drawn on other pages of the page's drawing set and none on this one; a unit's terminal is
drawn in a box cell of another unit, with every wire inside its own unit; or its far ends stand
only in other drawing sets (a unit's black box in its parent's set whose wire is a stub at the
unit's own page). Jumper routes do not meet. The count over the models below may only be zero.
The pump-station example lives in another repository, so these fixtures stand for it.

Decision layout-0216 adds two ratchets: no link marker stands on a terminal's path (a terminal is
drawn where its conductor ends, never referenced), and no copy stands unwired on a page where a
far end of it stands (the `same_page` cause).
"""

import importlib.util
import sys
import tempfile
from collections import defaultdict
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import fransys as fr
import pytest
from fransys_el import OPTIONS

from fransys_layout.engines import lay_out_schematic
from fransys_model.derive.facts.units import in_unit_subtree
from fransys_model.derive.indexes import build_indexes
from fransys_model.kernel import freeze
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    Page,
    PowerSymbol,
    Route,
    StarKind,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.enums import ConductorKind, FunctionKind
from fransys_model.vocab.tables import conductors, functions, items, ports

if TYPE_CHECKING:
    from collections.abc import Mapping

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
        "bank-pages-coarse": bank._built("3.0", 9).model,
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


def _unmet_copies(model: Any) -> list[tuple[Any, Any, dict[Any, set[Any]]]]:
    """Each `(page, function, placed)` terminal copy no wire meets there; `placed` maps a
    function to its pages."""
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
        if not set(ports_of.get(p.function, ())) & wired[p.page]:
            found.append((p.page, p.function, placed))
    return found


def _same_page(model: Any, function: Any, page: Any, placed: dict[Any, set[Any]]) -> bool:
    """A far end of the copy's terminal stands on `page`."""
    return any(
        page in placed.get(far, set()) | placed.get(far_port, set())
        for far_port, far in _far_ends(model, function)
    )


def loose_copies(model: Any) -> list[tuple]:
    """Each `(page, function)` terminal copy no wire meets there, for one of the four causes."""
    return [
        (page, function)
        for page, function, placed in _unmet_copies(model)
        if _no_wire(model, function)
        or _block_shape(model, function, page, placed)
        or _unwired_box_cell(model, function, page)
        or _other_set(model, function, page, placed)
    ]


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


def _on_terminal_path(model: Any, marker: Any, markers: Mapping[Any, Any]) -> bool:
    """A marker that is no off-page stub and whose own or partner port is a terminal's."""
    if marker.star is StarKind.OFF:
        return False
    kinds, port_records = functions(model), ports(model)
    partner = markers[marker.partner]
    return any(
        kinds[port_records[m.port].function].kind is FunctionKind.TERMINAL
        for m in (marker, partner)
    )


def _terminal_references(model: Any) -> int:
    """Link markers on a terminal's path: a reference where a terminal should be drawn."""
    markers = layout_of(model, LinkMarker)
    return sum(1 for m in markers.values() if _on_terminal_path(model, m, markers))


def test_a_terminal_fanned_out_to_groups_on_one_page_draws_no_reference() -> None:
    """The power-text model's X1:5 feeds four lamps on one page: its home joins them."""
    assert _terminal_references(_models()["power-text"]) == 0


@pytest.mark.xfail(
    strict=True,
    reason="model-0220: cabinet-discovery's X3:1-K1:4, a star wire between cells adjacent in one"
    " column, keeps its marker pair: the copy goes only where the terminal is not in the column",
)
def test_no_marker_stands_on_a_terminals_path() -> None:
    counts = {name: _terminal_references(m) for name, m in _models().items()}
    assert sum(counts.values()) == 0, counts


def test_the_markers_on_terminal_paths_stay_at_their_ceiling() -> None:
    """model-0220 took the count from 30 to 2 (one pair); it may only fall."""
    counts = {name: _terminal_references(m) for name, m in _models().items()}
    assert sum(counts.values()) <= 2, counts


def test_the_boundary_stub_model_still_has_an_off_stub() -> None:
    """Stubs into another set keep their marker. Dropping every OFF marker from the model, or a
    rule that routes stubs too, makes this fail."""
    markers = layout_of(_models()["boundary-stub"], LinkMarker).values()
    assert any(m.star is StarKind.OFF for m in markers)


@cache
def _fan_in() -> Any:
    module = _load(
        FIELD_CASES / "test_a_fan_in_onto_a_bridged_fuse_terminal_builds.py", "fan_in_for_copies"
    )
    return _field_unit(module, "_cab", "cab")


def _unwired_beside() -> dict[str, int]:
    models = {**_models(), "fan-in": _fan_in()}
    return {
        name: sum(
            1
            for page, function, placed in _unmet_copies(m)
            if _same_page(m, function, page, placed)
        )
        for name, m in models.items()
    }


@pytest.mark.xfail(
    strict=True,
    reason="model-0220: fan-in's U1/X1:24V:6, X2:1 and X2:2 stand in U1's black box in the"
    " top-level set, wired inside U1 only; the cabinet's X4:1 on page 2 ends harness W1's core 2,"
    " a line this count does not read",
)
def test_no_copy_stands_unwired_beside_its_far_end() -> None:
    counts = _unwired_beside()
    assert sum(counts.values()) == 0, counts


def test_the_unwired_copies_beside_a_far_end_stay_at_their_ceiling() -> None:
    """The four named in the xfail above; the count may only fall."""
    counts = _unwired_beside()
    assert sum(counts.values()) <= 4, counts


def _host(model: Any, key: tuple) -> Any:
    """The function whose key is the longest slice of `key` right after its "at"."""
    rest = key[key.index("at") + 1 :]
    hosts = [f for f in functions(model).values() if rest[: len(f.key)] == f.key]
    return max(hosts, key=lambda f: len(f.key), default=None)


def _unrouted_copies(model: Any) -> int:
    """Copies at a wire with no route on their page joining the terminal to its host."""
    ports_of = build_indexes(model).ports_by_function
    routes = list(layout_of(model, Route).values())
    kinds = functions(model)
    count = 0
    for p in layout_of(model, SymbolPlacement).values():
        if p.function not in kinds or kinds[p.function].kind is not FunctionKind.TERMINAL:
            continue
        if "at" not in p.key:
            continue
        host, own = _host(model, p.key), set(ports_of.get(p.function, ()))
        theirs = set(ports_of.get(host.id, ())) if host else set()
        joined = any(
            r.page == p.page and ({r.a, r.b} & own) and ({r.a, r.b} & theirs) for r in routes
        )
        count += not joined
    return count


def test_every_copy_at_a_wire_is_routed_to_its_host() -> None:
    models = {**_models(), "fan-in": _fan_in()}
    counts = {name: _unrouted_copies(m) for name, m in models.items()}
    assert sum(counts.values()) == 0, counts
