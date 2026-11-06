"""F2-F6 acceptance: parts, the findings policy, the export table, out_dir ownership."""

import sys
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import fransys as fr
import pytest
from _expected_codes import expect_codes
from fransys._exports import _Export, _exports, _file_safe
from fransys.pipeline import (
    BuildFailedError,
    BuildResult,
    _Drawn,
    _svgs,
    _svgs_cache,
)

from electrical_symbols import LIBRARY
from fransys_layout import DiagramLayout
from fransys_model.kernel import Draft, Finding, Id, Origin, Severity, make_id
from fransys_model.vocab import Document, DocumentPreset
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Function, Item, Port, Unit, UnitRelease
from fransys_model.vocab.enums import ConductorKind, FunctionKind, PartCategory, PortBoundary
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet, CoreFacet
from fransys_model.vocab.revision import Revision
from fransys_model.vocab.templates import FunctionTemplate, Part, PortTemplate

from ._board_and_rack import build_board_and_rack_model


def _error_finding(subject: Id[Any]) -> Finding:
    return Finding(
        code="DEMO_ERROR",
        severity=Severity.ERROR,
        subjects=(subject,),
        message="demo",
        fix="Write: x",
    )


def _warning_finding(subject: Id[Any]) -> Finding:
    return Finding(
        code="DEMO_WARNING",
        severity=Severity.WARNING,
        subjects=(subject,),
        message="demo",
        fix="Write: x",
    )


# -- F2: parts -----------------------------------------------------------------


def test_parts_with_no_packages_gives_an_empty_draft():
    draft = fr.parts()
    assert draft.records() == ()


def test_parts_loads_a_package():
    draft = fr.parts("demo_parts")
    assert draft.records()


# -- F5: the findings policy, no escape hatch -----------------------------------


def test_error_finding_blocks_every_export_and_raises_build_errors(demo_cabinet, tmp_path, demo_cabinet_result):
    subject = next(iter(demo_cabinet.tables["item"]))
    result = replace(demo_cabinet_result, findings=(_error_finding(subject),))
    out_dir = tmp_path / "out"
    with pytest.raises(BuildFailedError) as excinfo:
        fr.write(result, out_dir)
    assert excinfo.value.findings
    assert all(f.code == "DEMO_ERROR" for f in excinfo.value.findings)
    origin = demo_cabinet.origins[subject]
    assert f"{origin.file}:{origin.line}" in str(excinfo.value)
    assert not out_dir.exists() or list(out_dir.iterdir()) == []


def test_warning_finding_does_not_block_any_export(demo_cabinet, tmp_path, demo_cabinet_result):
    subject = next(iter(demo_cabinet.tables["item"]))
    result = replace(demo_cabinet_result, findings=(_warning_finding(subject),))
    out_dir = tmp_path / "out"
    written = fr.write(result, out_dir)
    assert written
    assert {"DEMO-1-v1.1-bom.csv", "DEMO-1-v1.1-overview.html"} <= {p.name for p in written}


def test_a_blocked_write_draws_no_svg_where_the_unblocked_write_draws_them(demo_cabinet, tmp_path, demo_cabinet_result):
    """0028 amended (model-0077): an errored build's intermediates hold no drawn page.

    The positive twin is `test_a_harness_svg_intermediate_has_no_colon_in_its_name`: the same
    model with no finding writes its SVGs.
    """
    subject = next(iter(demo_cabinet.tables["item"]))
    result = replace(demo_cabinet_result, findings=(_error_finding(subject),))
    out_dir, intermediates = tmp_path / "out", tmp_path / "intermediates"
    with pytest.raises(BuildFailedError):
        fr.write(result, out_dir, intermediates=intermediates)
    assert intermediates.is_dir()
    assert list(intermediates.glob("*.svg")) == []


# -- Windows page-key filenames (ruling 2026-09-22) ----------------------


def test_file_safe_strips_the_colon_from_a_page_key():
    """`render_id` renders a page key as `kind:value` (e.g. `item:<hex>`)."""
    assert ":" not in _file_safe("item:0123456789abcdef")


def test_a_harness_svg_intermediate_has_no_colon_in_its_name(tmp_path, demo_cabinet_result):
    """`write` names every render SVG from a sanitised page key, so the file really exists.

    The SVG this fixture writes is its `SYSTEM` document's rendered `SCHEMATIC` page.
    """
    result = replace(demo_cabinet_result, findings=())
    intermediates = tmp_path / "intermediates"
    fr.write(result, tmp_path / "out", intermediates=intermediates)
    svgs = list(intermediates.glob("*.svg"))
    assert svgs
    assert all(":" not in path.name for path in svgs)
    assert all(path.stat().st_size > 0 for path in svgs)


_WINDOWS_FORBIDDEN_CHARS = frozenset('<>:"/\\|?*') | {chr(code) for code in range(32)}
_WINDOWS_RESERVED_STEMS = frozenset({"CON", "PRN", "AUX", "NUL"} | {f"COM{n}" for n in range(1, 10)} | {f"LPT{n}" for n in range(1, 10)})


def _windows_forbidden(name: str) -> bool:
    """True when Windows refuses `name` as a file name, whatever OS the test runs on."""
    return (
        any(char in _WINDOWS_FORBIDDEN_CHARS for char in name)
        or name.split(".", maxsplit=1)[0].upper() in _WINDOWS_RESERVED_STEMS
        or name.endswith((".", " "))
    )


@pytest.mark.parametrize("bad", ["a:b.svg", "CON.txt", "x .", "x.", "aux", "a\x01b", "a|b"])
def test_windows_forbidden_flags_a_bad_name(bad):
    assert _windows_forbidden(bad)


@pytest.mark.parametrize("good", ["DEMO-1-v1.1-bom.csv", "netlist-PCB1.net", "item-0123.svg"])
def test_windows_forbidden_passes_a_good_name(good):
    assert not _windows_forbidden(good)


@pytest.mark.parametrize("fixture", ["demo_cabinet"])
def test_no_written_file_has_a_name_windows_forbids(fixture, request, tmp_path, monkeypatch):
    """Every file `write` puts out is legal on Windows, checked on the names, on every OS.

    A listing cannot show it: a colon name on NTFS opens an alternate data stream and never
    lists. So the names come from what `write` computes: the returned paths, the keys of
    """
    built = request.getfixturevalue(f"{fixture}_result")
    model = built.model
    result = BuildResult(model=model, findings=(), drawings=built.drawings, page_svgs=built.page_svgs)
    names: set[str] = set()
    original = Path.write_bytes

    def recording(self, data):
        names.add(self.name)
        return original(self, data)

    monkeypatch.setattr(Path, "write_bytes", recording)
    written = fr.write(result, tmp_path / "out", intermediates=tmp_path / "intermediates")
    monkeypatch.undo()
    names |= {path.name for path in written}
    _svgs_cache.cache_clear()
    svgs = _svgs(_Drawn(model, result.drawings, DiagramLayout(diagrams=()), LIBRARY, result.page_svgs))
    drawn = _Drawn(model, result.drawings, DiagramLayout(diagrams=()), LIBRARY, svgs)
    names |= {Path(n).name for n in _exports(_Export(drawn, result.settings))}
    assert names
    assert [name for name in sorted(names) if _windows_forbidden(name)] == []


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="NTFS alternate data streams: a colon in a file name opens one on Windows only; on Linux the colon is legal and the file appears",
)
def test_the_colon_bug_can_fail_the_naive_way(demo_cabinet, tmp_path, demo_cabinet_result):
    """Can-fail twin: writing the RAW (unsanitised) page key produces no visible `.svg`.

    Proves `_file_safe` is load-bearing, not cosmetic: skip it (write the raw
    `render_id`-shaped key straight into the file name) and the page silently
    """
    _svgs_cache.cache_clear()
    board = demo_cabinet_result
    svgs = _svgs(
        _Drawn(
            demo_cabinet,
            board.drawings,
            DiagramLayout(diagrams=()),
            LIBRARY,
            board.page_svgs,
        )
    )
    assert svgs
    intermediates = tmp_path / "intermediates"
    intermediates.mkdir()
    for page_key, svg in svgs.items():
        assert ":" in page_key  # the bug needs an un-sanitised key to bite
        (intermediates / f"{page_key}.svg").write_bytes(svg.encode("utf-8"))
    assert list(intermediates.glob("*.svg")) == []


# -- F6: out_dir ownership --------------------------------------------------------


def _plant_stale_files(out_dir):
    out_dir.mkdir(parents=True)
    (out_dir / "bom.csv").write_text("stale", encoding="utf-8")
    (out_dir / "old.pdf").write_bytes(b"stale")
    (out_dir / "notes.txt").write_text("keep me", encoding="utf-8")
    (out_dir / "keep").mkdir()
    (out_dir / "keep" / "inside.csv").write_text("keep me too", encoding="utf-8")


def _assert_only_exports_removed(out_dir):
    names = {p.name for p in out_dir.iterdir()}
    assert "old.pdf" not in names
    assert "bom.csv" not in names
    assert (out_dir / "notes.txt").read_text(encoding="utf-8") == "keep me"
    assert "keep" in names
    assert (out_dir / "keep" / "inside.csv").exists()


def test_stale_exports_are_removed_on_a_successful_write(tmp_path, demo_cabinet_result):
    out_dir = tmp_path / "out"
    _plant_stale_files(out_dir)
    result = replace(demo_cabinet_result, findings=())
    fr.write(result, out_dir)
    _assert_only_exports_removed(out_dir)
    assert (out_dir / "data" / "DEMO-1-v1.1-bom.csv").read_text(encoding="utf-8") != "stale"


def test_stale_exports_are_removed_on_the_raise_path(demo_cabinet, tmp_path, demo_cabinet_result):
    out_dir = tmp_path / "out"
    _plant_stale_files(out_dir)
    subject = next(iter(demo_cabinet.tables["item"]))
    result = replace(demo_cabinet_result, findings=(_error_finding(subject),))
    with pytest.raises(BuildFailedError):
        fr.write(result, out_dir)
    _assert_only_exports_removed(out_dir)


# -- F6: naming ------------------------------------------------------------------


def test_terminal_export_is_one_file_for_every_strip(tmp_path, demo_cabinet_result):
    result = replace(demo_cabinet_result, findings=())
    written = fr.write(result, tmp_path / "out")
    names = {p.name for p in written}
    assert "DEMO-1-v1.1-terminals.csv" in names
    assert not [p for p in tmp_path.joinpath("out").iterdir() if p.suffix in {".csv", ".xml"}]
    assert all(p.parent.name == "data" for p in written if p.suffix in {".csv", ".xml"})


def test_connector_export_is_one_file_and_the_rack_export_is_named_from_its_reference(tmp_path):
    model = build_board_and_rack_model()
    result = BuildResult(model=model, findings=())
    written = fr.write(result, tmp_path / "out")
    names = {p.name for p in written}
    assert "connectors.csv" in names
    assert "wago-R1.xml" in names


def test_board_netlist_is_written_to_intermediates_named_from_its_reference(tmp_path):
    model = build_board_and_rack_model()
    result = BuildResult(model=model, findings=())
    intermediates = tmp_path / "intermediates"
    fr.write(result, tmp_path / "out", intermediates=intermediates)
    assert (intermediates / "netlist-PCB1.net").exists()


def test_out_dir_never_receives_an_svg(tmp_path, demo_cabinet_result):
    """Decision-0011 regression guard: `out_dir` holds exports only, never a page SVG.

    `_exports()` cannot emit an `.svg` key today (it never calls a drawing function), so
    this is "true by construction" -- exactly why it must stay a live assertion: a future
    """
    result = replace(demo_cabinet_result, findings=())
    out_dir, intermediates = tmp_path / "out", tmp_path / "intermediates"
    written = fr.write(result, out_dir, intermediates=intermediates)
    assert written
    assert not any(path.suffix == ".svg" for path in written)
    assert not list(out_dir.glob("*.svg"))
    assert list(intermediates.glob("*.svg"))


# -- Determinism -------------------------------------------------------------------


def test_two_writes_of_one_result_give_byte_equal_files(tmp_path, demo_cabinet_result):
    result = replace(demo_cabinet_result, findings=())
    first = fr.write(result, tmp_path / "out1")
    second = fr.write(result, tmp_path / "out2")
    assert {p.name for p in first} == {p.name for p in second}
    for path in first:
        twin = tmp_path / "out2" / path.relative_to(tmp_path / "out1")
        assert twin.read_bytes() == path.read_bytes()


_TEXT_SUFFIXES = {".csv", ".xml", ".md", ".json", ".html", ".txt"}


def test_every_text_export_has_no_bom_and_no_carriage_return(tmp_path, demo_cabinet_result):
    """Guide build.md: UTF-8, no byte order mark, `\\n` line ends, on every OS."""
    result = replace(demo_cabinet_result, findings=())
    written = [p for p in fr.write(result, tmp_path / "out") if p.suffix in _TEXT_SUFFIXES]
    assert {".csv"} <= {p.suffix for p in written}  # examined: text exports really were written
    bad = [p.name for p in written if p.read_bytes().startswith(b"\xef\xbb\xbf") or b"\r" in p.read_bytes()]
    assert bad == []


# -- F4: check ordering -------------------------------------------------------------


def test_check_orders_error_then_warning_then_info(demo_cabinet, demo_cabinet_result):
    subject = next(iter(demo_cabinet.tables["item"]))
    findings = (
        Finding(code="Z_INFO", severity=Severity.INFO, subjects=(subject,), message="z"),
        Finding(
            code="A_ERROR",
            severity=Severity.ERROR,
            subjects=(subject,),
            message="a",
            fix="Write: x",
        ),
        Finding(
            code="M_WARNING",
            severity=Severity.WARNING,
            subjects=(subject,),
            message="m",
            fix="Write: x",
        ),
    )
    result = replace(demo_cabinet_result, findings=findings)
    resolved = fr.check(result)
    rank = {"error": 0, "warning": 1, "info": 2}
    severities = [f.severity for f in resolved]
    assert severities == sorted(severities, key=lambda s: rank[s.value])
    assert resolved[0].code == "A_ERROR"


def test_check_resolves_every_subject_through_describe(demo_cabinet):
    subject = next(iter(demo_cabinet.tables["item"]))
    origin = demo_cabinet.origins[subject]
    result = BuildResult(
        model=demo_cabinet,
        findings=(_warning_finding(subject),),
    )
    (resolved,) = (f for f in fr.check(result) if f.code == "DEMO_WARNING")
    assert f"{origin.file}:{origin.line}" in resolved.message


def test_check_calls_kicad_check_for_every_board():
    model = build_board_and_rack_model()
    result = BuildResult(model=model, findings=())
    findings = fr.check(result)
    # the SYSTEM document of the board model has no list rows or cable to print (INFO only)
    assert {f.code for f in findings} <= {"DOCUMENT_EMPTY_LIST", "DOCUMENT_NO_TOP_LEVEL_CABLES"}
    assert {f.severity.name for f in findings} <= {"INFO"}


def _wired_to_a_partner(draft: Draft, port: Port, origin: Origin) -> None:
    """Conduct `port` to a part-less terminal's port, so its function is drawn (layout-0218)."""
    partner_item = Item(
        id=make_id(Item, ("t",)),
        key=("t",),
        part=None,
        parent=None,
        position=None,
        tag="X9",
        description="Invented terminal",
    )
    partner_function = Function(
        id=make_id(Function, ("t", "f")),
        key=("t", "f"),
        item=partner_item.id,
        template=None,
        name="f",
        kind=FunctionKind.GENERIC,
    )
    partner_port = Port(
        id=make_id(Port, ("t", "f", "1")),
        key=("t", "f", "1"),
        function=partner_function.id,
        template=None,
        name="1",
        boundary=PortBoundary.GENERIC,
    )
    conductor = Conductor(
        id=make_id(Conductor, ("wire-1",)),
        key=("wire-1",),
        a=port.id,
        b=partner_port.id,
        kind=ConductorKind.WIRE,
        carrier=None,
    )
    draft.extend([partner_item, partner_function, partner_port, conductor], origin=origin)


# -- F4/F5: SYMBOL_PORT_MISSING (examples gap G10, decision 0018) ---------------


_PART_FILE = "examples/demo-parts/demo_parts/parts/broken-relay.toml"
# The `[part]` header's own line: distinct from `_FUNCTION_ORIGIN` below, the way
# `fransys_parts.loader` gives a `Part` and its `FunctionTemplate`s different lines of
# one file, so a test can tell "the part file, the `Part`'s own line" apart from "the part
# file, that function's line" -- both fallbacks the finding's origin can resolve to.
_PART_HEADER_ORIGIN = Origin(file=_PART_FILE, line=3, note="invented")
_FUNCTION_ORIGIN = Origin(file=_PART_FILE, line=10, note="invented")
_DESIGN_ORIGIN = Origin(file="packages/fransys/tests/test_acceptance.py", line=1, note="invented")


def _schematic_document(name: str, item: Id[Any]) -> Document:
    """A `CABINET_SCHEMATIC` document of `item`: PS1/PS2's "layout runs only on a model with a
    document" gate (MODEL-BUILD, decision 0037) needs one before `fr.build` will call
    `lay_out_schematic` at all -- these symbol-port tests fail inside that call,
    so without this the error never fires and `SYMBOL_PORT_MISSING` never appears.
    """
    key = ("document", name)
    return Document(
        id=make_id(Document, key),
        key=key,
        preset=DocumentPreset.CABINET_SCHEMATIC,
        location=None,
        item=item,
        cover="Invented cover text.",
        notes=None,
    )


def _model_with_a_symbol_port_mismatch() -> tuple[Draft, Id[Any], Id[Any]]:
    """A part whose one port name matches no symbol port: examples gap G10, decision 0018.

    `coil` is `DEFAULT_RULES`' own rule (`operating-device`, no `port_map`); its symbol has
    ports `in`/`out`, never `WRONG`. This function's `FunctionTemplate` declares one port
    """
    part_key = ("part", "Demo", "DEMO-BROKEN-RLY")
    part = Part(
        id=make_id(Part, part_key),
        key=part_key,
        mpn="DEMO-BROKEN-RLY",
        manufacturer="Demo",
        description="Invented relay whose coil port map is broken",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="K",
    )
    function_template_key = (*part_key, "function", "coil")
    function_template = FunctionTemplate(
        id=make_id(FunctionTemplate, function_template_key),
        key=function_template_key,
        part=part.id,
        name="coil",
        kind=FunctionKind.COIL,
    )
    port_template_key = (*function_template_key, "port", "WRONG")
    port_template = PortTemplate(
        id=make_id(PortTemplate, port_template_key),
        key=port_template_key,
        function=function_template.id,
        name="WRONG",
        boundary=PortBoundary.GENERIC,
    )

    item = Item(
        id=make_id(Item, ("item", "k1")),
        key=("item", "k1"),
        part=part.id,
        parent=None,
        position=None,
        tag="K1",
        description="Invented",
    )
    function_key = ("function", "k1", "coil")
    function = Function(
        id=make_id(Function, function_key),
        key=function_key,
        item=item.id,
        template=function_template.id,
        name="coil",
        kind=FunctionKind.COIL,
    )
    port_key = (*function_key, "port", "WRONG")
    port = Port(
        id=make_id(Port, port_key),
        key=port_key,
        function=function.id,
        template=port_template.id,
        name="WRONG",
        boundary=PortBoundary.GENERIC,
    )

    draft = Draft()
    draft.add(part, origin=_PART_HEADER_ORIGIN)
    draft.extend([function_template, port_template], origin=_FUNCTION_ORIGIN)
    draft.extend([item, function, port, _schematic_document("symbol-port-mismatch", item.id)], origin=_DESIGN_ORIGIN)
    # layout-0218: an unconnected function is drawn on no page, so the mismatch needs a wire.
    _wired_to_a_partner(draft, port, _DESIGN_ORIGIN)
    return draft, part.id, port_template.id


def test_symbol_port_missing_becomes_one_error_finding():
    """PART 1 test (a): `fr.check` reports the symbol-port refusal as one finding.

    Exactly one `SYMBOL_PORT_MISSING`, `ERROR`. Asserted twice: on `result.findings` (before
    `describe`), the raw `code`/`severity`/`message`/`subjects` are exact -- the message
    """
    draft, _part_id, port_template_id = _model_with_a_symbol_port_mismatch()
    result = fr.build(draft)

    expect_codes(result, "SYMBOL_PORT_MISSING")
    raw = [f for f in result.findings if f.code == "SYMBOL_PORT_MISSING"]
    assert len(raw) == 1
    assert raw[0].severity is Severity.ERROR
    assert raw[0].subjects == (port_template_id,)
    assert raw[0].message == ("part 'DEMO-BROKEN-RLY': model port 'WRONG' has no port on symbol 'operating-device'")

    resolved = [f for f in fr.check(result) if f.code == "SYMBOL_PORT_MISSING"]
    assert len(resolved) == 1
    assert f"{_FUNCTION_ORIGIN.file}:{_FUNCTION_ORIGIN.line}" in resolved[0].message
    assert f":{_PART_HEADER_ORIGIN.line} " not in resolved[0].message
    assert _DESIGN_ORIGIN.file not in resolved[0].message


def test_symbol_port_missing_blocks_write_and_writes_nothing(tmp_path):
    """PART 1 test (b): `fr.write` raises the findings-policy error and writes no file."""
    draft, _part_id, _port_template_id = _model_with_a_symbol_port_mismatch()
    result = fr.build(draft)
    out_dir = tmp_path / "out"
    with pytest.raises(BuildFailedError):
        fr.write(result, out_dir)
    expect_codes(result, "SYMBOL_PORT_MISSING")
    assert not out_dir.exists() or list(out_dir.iterdir()) == []


def _model_with_a_part_less_symbol_mismatch() -> tuple[Draft, Id[Any]]:
    """A part-less item's function, authored directly, with a port matching no symbol port.

    Reachable: the model's vocabulary notes document this shape directly --
    "Items without a part (`part=None`) declare functions and ports directly. This is for early
    """
    item = Item(
        id=make_id(Item, ("item", "k3")),
        key=("item", "k3"),
        part=None,
        parent=None,
        position=None,
        tag="K3",
        description="Invented, no part: design/vocabulary.md 7's early-design shape",
    )
    function_key = ("function", "k3", "coil")
    function = Function(
        id=make_id(Function, function_key),
        key=function_key,
        item=item.id,
        template=None,
        name="coil",
        kind=FunctionKind.COIL,
    )
    port_key = (*function_key, "port", "WRONG")
    port = Port(
        id=make_id(Port, port_key),
        key=port_key,
        function=function.id,
        template=None,
        name="WRONG",
        boundary=PortBoundary.GENERIC,
    )

    draft = Draft()
    draft.extend(
        [item, function, port, _schematic_document("part-less-symbol-mismatch", item.id)],
        origin=_DESIGN_ORIGIN,
    )
    # layout-0218: an unconnected function is drawn on no page, so the mismatch needs a wire.
    _wired_to_a_partner(draft, port, _DESIGN_ORIGIN)
    return draft, function.id


def test_symbol_port_missing_falls_back_to_the_function_with_no_part_at_all():
    """The part-less case: no `Part` and no `PortTemplate`, so the origin is the function.

    Also confirms the shape is real: `ITEM_WITHOUT_PART` fires alongside it (`INFO`, never
    blocking), and layout still runs and raises regardless.
    """
    draft, function_id = _model_with_a_part_less_symbol_mismatch()
    result = fr.build(draft)

    assert any(f.code == "ITEM_WITHOUT_PART" for f in result.findings)
    expect_codes(result, "SYMBOL_PORT_MISSING")
    raw = [f for f in result.findings if f.code == "SYMBOL_PORT_MISSING"]
    assert len(raw) == 1
    assert raw[0].severity is Severity.ERROR
    assert raw[0].subjects == (function_id,)
    assert raw[0].message == ("part 'no part': model port 'WRONG' has no port on symbol 'operating-device'")


# -- decision 0016: cables.csv, per unit and for the system -----------


def _model_with_a_unit_and_a_top_level_cable() -> tuple[Draft, Id[Any]]:
    """A one-item unit `U1` and one top-level (`unit=None`) cable `W1` with a single core.

    The cable is top-level, so the unit's own `cables.csv` is written but has no rows. The
    fixture keeps the cable outside `unit`, the way the "cable drawings" rule already treats
    """
    release = UnitRelease(
        id=make_id(UnitRelease, ("unit_release", "unit-one", "1", "1")),
        key=("unit_release", "unit-one", "1", "1"),
        name="unit-one",
        version=1,
        revision=1,
        interface="1",
    )
    unit = Unit(id=make_id(Unit, ("u1",)), key=("u1",), release=release.id, parent=None)
    unit_revision = Revision(
        id=make_id(Revision, ("u1", "revision", "1")),
        key=("u1", "revision", "1"),
        release=release.id,
        version=1,
        revision=1,
        date="2026-01-01",
        text="First release",
        created="XX",
    )
    unit_item = Item(
        id=make_id(Item, ("boxed",)),
        key=("boxed",),
        part=None,
        parent=None,
        position=None,
        tag="A1",
        description="boxed",
        installed=True,
        unit=unit.id,
    )
    cable_part = Part(
        id=make_id(Part, ("cab1",)),
        key=("cab1",),
        mpn="SIM-CAB1",
        manufacturer="Example Co",
        description="Invented one-core cable",
        category=PartCategory.CABLE,
        class_code="W",
    )
    cable_product = CableProductFacet(
        id=make_id(CableProductFacet, ("cab1", "product")),
        key=("cab1", "product"),
        subject=cable_part.id,
        core_colours=("BN",),
        gauge_mm2=Decimal("0.5"),
        shielded=False,
    )
    cable_item = Item(
        id=make_id(Item, ("w1",)),
        key=("w1",),
        part=cable_part.id,
        parent=None,
        position=None,
        tag="W1",
        description="cable",
        installed=True,
        unit=None,
    )
    cable_facet = CableFacet(
        id=make_id(CableFacet, ("w1", "cable")),
        key=("w1", "cable"),
        subject=cable_item.id,
        length_mm=None,
    )
    end_a_item = Item(
        id=make_id(Item, ("ea",)),
        key=("ea",),
        part=None,
        parent=None,
        position=None,
        tag="EA",
        description="end a",
        installed=True,
        unit=None,
    )
    end_a_fn = Function(
        id=make_id(Function, ("ea", "f")),
        key=("ea", "f"),
        item=end_a_item.id,
        template=None,
        name="f",
        kind=FunctionKind.GENERIC,
    )
    end_a_port = Port(
        id=make_id(Port, ("ea", "f", "1")),
        key=("ea", "f", "1"),
        function=end_a_fn.id,
        template=None,
        name="1",
        boundary=PortBoundary.GENERIC,
    )
    end_b_item = Item(
        id=make_id(Item, ("eb",)),
        key=("eb",),
        part=None,
        parent=None,
        position=None,
        tag="EB",
        description="end b",
        installed=True,
        unit=None,
    )
    end_b_fn = Function(
        id=make_id(Function, ("eb", "f")),
        key=("eb", "f"),
        item=end_b_item.id,
        template=None,
        name="f",
        kind=FunctionKind.GENERIC,
    )
    end_b_port = Port(
        id=make_id(Port, ("eb", "f", "1")),
        key=("eb", "f", "1"),
        function=end_b_fn.id,
        template=None,
        name="1",
        boundary=PortBoundary.GENERIC,
    )
    core = Conductor(
        id=make_id(Conductor, ("core-1",)),
        key=("core-1",),
        a=end_a_port.id,
        b=end_b_port.id,
        kind=ConductorKind.CORE,
        carrier=cable_item.id,
    )
    core_facet = CoreFacet(
        id=make_id(CoreFacet, ("core-1", "facet")),
        key=("core-1", "facet"),
        subject=core.id,
        index=1,
    )

    draft = Draft()
    draft.extend(
        [
            release,
            unit,
            unit_revision,
            unit_item,
            cable_part,
            cable_product,
            cable_item,
            cable_facet,
            end_a_item,
            end_a_fn,
            end_a_port,
            end_b_item,
            end_b_fn,
            end_b_port,
            core,
            core_facet,
        ],
        origin=_DESIGN_ORIGIN,
    )
    return draft, unit.id


def test_write_includes_cables_csv_for_the_system_and_for_a_unit(tmp_path):
    """`cables.csv` is written both whole-system and per unit; `overview.html` is system-only.

    `unit=None` writes both files; `unit=<a real unit>` writes `cables.csv` but not
    `overview.html`, on the same model -- a top-level cable and a unit-owned item both exist
    """
    draft, unit_id = _model_with_a_unit_and_a_top_level_cable()
    result = fr.build(draft)

    whole = fr.write(result, tmp_path / "whole", unit=None)
    assert any(p.name.endswith("cables.csv") for p in whole)
    assert any(p.name.endswith("overview.html") for p in whole)

    scoped = fr.write(result, tmp_path / "scoped", unit=unit_id)
    assert any(p.name.endswith("cables.csv") for p in scoped)
    assert not any(p.name.endswith("overview.html") for p in scoped)  # the system-view rule
