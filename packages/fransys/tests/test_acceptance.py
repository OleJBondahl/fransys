"""F2-F6 acceptance: parts, the findings policy, the export table, out_dir ownership."""

import sys
from decimal import Decimal
from pathlib import Path

import fransys as fr
import pytest
from fransys.pipeline import (
    BuildErrors,
    BuildResult,
    ExportNameClash,
    _exports,
    _file_safe,
    _resolved,
    _svgs,
    _svgs_cache,
    _symbol_port_missing_finding,
)

from fransys_layout.engines.schematic import lay_out_schematic
from fransys_layout.geometry import SymbolPortError
from fransys_model.kernel import Draft, Finding, Id, Origin, Severity, freeze, make_id
from fransys_model.vocab import Document, DocumentPreset, PageKind
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Function, Item, Port, Unit, UnitRelease
from fransys_model.vocab.enums import ConductorKind, FunctionKind, PartCategory, PortRole
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet, CoreFacet
from fransys_model.vocab.facets.pcb import PcbFacet
from fransys_model.vocab.revision import Revision
from fransys_model.vocab.templates import FunctionTemplate, Part, PortTemplate

from ._board_and_rack import build_board_and_rack_model


def _error_finding(subject: Id) -> Finding:
    return Finding(code="DEMO_ERROR", severity=Severity.ERROR, subjects=(subject,), message="demo")


def _warning_finding(subject: Id) -> Finding:
    return Finding(
        code="DEMO_WARNING", severity=Severity.WARNING, subjects=(subject,), message="demo"
    )


# -- F2: parts -----------------------------------------------------------------


def test_parts_with_no_packages_gives_an_empty_draft():
    draft = fr.parts()
    assert draft.records() == ()


def test_parts_loads_a_package():
    draft = fr.parts("demo_parts")
    assert draft.records()


# -- F5: the findings policy, no escape hatch -----------------------------------


def test_error_finding_blocks_every_export_and_raises_build_errors(demo_cabinet, tmp_path):
    subject = next(iter(demo_cabinet.tables["item"]))
    result = BuildResult(model=demo_cabinet, findings=(_error_finding(subject),))
    out_dir = tmp_path / "out"
    with pytest.raises(BuildErrors) as excinfo:
        fr.write(result, out_dir)
    assert excinfo.value.findings
    assert all(f.code == "DEMO_ERROR" for f in excinfo.value.findings)
    origin = demo_cabinet.origins[subject]
    assert f"{origin.file}:{origin.line}" in str(excinfo.value)
    assert not out_dir.exists() or list(out_dir.iterdir()) == []


def test_warning_finding_does_not_block_any_export(demo_cabinet, tmp_path):
    subject = next(iter(demo_cabinet.tables["item"]))
    result = BuildResult(model=demo_cabinet, findings=(_warning_finding(subject),))
    out_dir = tmp_path / "out"
    written = fr.write(result, out_dir)
    assert written
    assert {"DEMO-1-v1.1-bom.csv", "DEMO-1-v1.1-overview.html"} <= {p.name for p in written}


def test_a_blocked_write_draws_no_svg_where_the_unblocked_write_draws_them(
    demo_harness_with_board, tmp_path
):
    """0028 amended (model-0077): an errored build's intermediates hold no drawn page.

    The positive twin is `test_a_harness_svg_intermediate_has_no_colon_in_its_name`: the same
    model with no finding writes its harness SVGs. This model has no board and no document, so
    nothing but the drawings would land in the directory.

    UNDO: pipeline.write `svgs = {} if _has_error(result.findings) else _svgs(model)` ->
    `svgs = _svgs(model)` (the SCHEMATIC page's SVG is written again).
    """
    subject = next(iter(demo_harness_with_board.tables["item"]))
    result = BuildResult(model=demo_harness_with_board, findings=(_error_finding(subject),))
    out_dir, intermediates = tmp_path / "out", tmp_path / "intermediates"
    with pytest.raises(BuildErrors):
        fr.write(result, out_dir, intermediates=intermediates)
    assert intermediates.is_dir()
    assert list(intermediates.glob("*.svg")) == []


# -- Windows page-key filenames (orchestrator ruling 2026-09-22) ----------------------


def test_file_safe_strips_the_colon_from_a_page_key():
    """`render_id` renders a page key as `kind:value` (e.g. `item:<hex>`, spec F6)."""
    assert ":" not in _file_safe("item:0123456789abcdef")


def test_a_harness_svg_intermediate_has_no_colon_in_its_name(demo_harness_with_board, tmp_path):
    """`write` names every render SVG from a sanitised page key, so the file really exists.

    CT1: `demo_harness_with_board`'s own cable page is a Typst table now, no SVG; the one SVG
    this fixture still writes is its `SYSTEM` document's rendered `SCHEMATIC` page
    (`fransys_render.pages`), the same `_file_safe` sanitising this test has always pinned.
    `:` is valid in a POSIX file name but not mid-name on Windows: it opens an NTFS
    alternate data stream instead of raising, so a naive `f"{page_key}.svg"` write
    silently writes zero bytes to a visible `.svg` file -- the failure mode this test
    guards against is not an exception, it is a page that quietly never gets drawn.
    """
    result = BuildResult(model=demo_harness_with_board, findings=())
    intermediates = tmp_path / "intermediates"
    fr.write(result, tmp_path / "out", intermediates=intermediates)
    svgs = list(intermediates.glob("*.svg"))
    assert svgs
    assert all(":" not in path.name for path in svgs)
    assert all(path.stat().st_size > 0 for path in svgs)


_WINDOWS_FORBIDDEN_CHARS = frozenset('<>:"/\\|?*') | {chr(code) for code in range(32)}
_WINDOWS_RESERVED_STEMS = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{n}" for n in range(1, 10)}
    | {f"LPT{n}" for n in range(1, 10)}
)


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


@pytest.mark.parametrize("fixture", ["demo_harness_with_board", "demo_cabinet"])
def test_no_written_file_has_a_name_windows_forbids(fixture, request, tmp_path, monkeypatch):
    """Every file `write` puts out is legal on Windows, checked on the names, on every OS.

    A listing cannot show it: a colon name on NTFS opens an alternate data stream and never
    lists. So the names come from what `write` computes: the returned paths, the keys of
    `_exports`, and every path `Path.write_bytes` receives during the write (the intermediates).
    """
    model = request.getfixturevalue(fixture)
    result = BuildResult(model=model, findings=())
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
    names |= set(_exports(model, _svgs(model)))
    assert names
    assert [name for name in sorted(names) if _windows_forbidden(name)] == []


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="NTFS alternate data streams: a colon in a file name opens one on Windows only; "
    "on Linux the colon is legal and the file appears",
)
def test_the_colon_bug_can_fail_the_naive_way(demo_harness_with_board, tmp_path):
    """Can-fail twin: writing the RAW (unsanitised) page key produces no visible `.svg`.

    Proves `_file_safe` is load-bearing, not cosmetic: skip it (write the raw
    `render_id`-shaped key straight into the file name) and the page silently
    disappears -- no exception, just an empty `intermediates` directory.
    """
    _svgs_cache.cache_clear()
    svgs = _svgs(demo_harness_with_board)
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


def test_stale_exports_are_removed_on_a_successful_write(demo_cabinet, tmp_path):
    out_dir = tmp_path / "out"
    _plant_stale_files(out_dir)
    result = BuildResult(model=demo_cabinet, findings=())
    fr.write(result, out_dir)
    names = {p.name for p in out_dir.iterdir()}
    assert "old.pdf" not in names
    assert "bom.csv" not in names
    assert (out_dir / "DEMO-1-v1.1-bom.csv").read_text(encoding="utf-8") != "stale"
    assert "notes.txt" in names
    assert (out_dir / "notes.txt").read_text(encoding="utf-8") == "keep me"
    assert "keep" in names
    assert (out_dir / "keep" / "inside.csv").exists()


def test_stale_exports_are_removed_on_the_raise_path(demo_cabinet, tmp_path):
    out_dir = tmp_path / "out"
    _plant_stale_files(out_dir)
    subject = next(iter(demo_cabinet.tables["item"]))
    result = BuildResult(model=demo_cabinet, findings=(_error_finding(subject),))
    with pytest.raises(BuildErrors):
        fr.write(result, out_dir)
    names = {p.name for p in out_dir.iterdir()}
    assert "old.pdf" not in names
    assert "bom.csv" not in names
    assert "notes.txt" in names
    assert (out_dir / "notes.txt").read_text(encoding="utf-8") == "keep me"
    assert "keep" in names
    assert (out_dir / "keep" / "inside.csv").exists()


# -- F6: naming ------------------------------------------------------------------


def test_terminal_export_is_named_from_the_strip_reference(demo_cabinet, tmp_path):
    result = BuildResult(model=demo_cabinet, findings=())
    written = fr.write(result, tmp_path / "out")
    names = {p.name for p in written}
    assert "DEMO-1-v1.1-terminals-C1-X1.csv" in names


def test_board_and_rack_exports_are_named_from_their_reference(tmp_path):
    model = build_board_and_rack_model()
    result = BuildResult(model=model, findings=())
    written = fr.write(result, tmp_path / "out")
    names = {p.name for p in written}
    assert "connectors-PCB1.csv" in names
    assert "wago-R1.xml" in names


def test_board_netlist_is_written_to_intermediates_named_from_its_reference(tmp_path):
    model = build_board_and_rack_model()
    result = BuildResult(model=model, findings=())
    intermediates = tmp_path / "intermediates"
    fr.write(result, tmp_path / "out", intermediates=intermediates)
    assert (intermediates / "netlist-PCB1.net").exists()


def test_out_dir_never_receives_an_svg(demo_harness_with_board, tmp_path):
    """Decision-0011 regression guard: `out_dir` holds exports only, never a page SVG.

    `_exports()` cannot emit an `.svg` key today (it never calls a drawing function), so
    this is "true by construction" -- exactly why it must stay a live assertion: a future
    change to `_exports()` (adding a drawing leg) could reintroduce a page SVG into
    `out_dir` with nothing else here to catch it. `demo_harness_with_board` guarantees at
    least one SVG actually exists (in intermediates), so this is not a vacuous check.
    """
    result = BuildResult(model=demo_harness_with_board, findings=())
    out_dir, intermediates = tmp_path / "out", tmp_path / "intermediates"
    written = fr.write(result, out_dir, intermediates=intermediates)
    assert written
    assert not any(path.suffix == ".svg" for path in written)
    assert not list(out_dir.glob("*.svg"))
    assert list(intermediates.glob("*.svg"))


_CLASH_ORIGIN = Origin(file="test_acceptance.py", line=1, note="deliberate clash")


def _clashing_boards_model():
    """Two board items sharing one designation and no placement, so `_subjects.ref` collides."""
    parts_and_boards = []
    for suffix in ("a", "b"):
        part = Part(
            id=make_id(Part, (f"board-{suffix}",)),
            key=(f"board-{suffix}",),
            mpn=f"SIM-BOARD-{suffix}",
            manufacturer="Example Co",
            description="Invented board",
            category=PartCategory.BOARD,
            class_code="A",
        )
        pcb = PcbFacet(
            id=make_id(PcbFacet, (f"board-{suffix}", "pcb")),
            key=(f"board-{suffix}", "pcb"),
            subject=part.id,
            revision="A",
        )
        item = Item(
            id=make_id(Item, (f"board-item-{suffix}",)),
            key=(f"board-item-{suffix}",),
            part=part.id,
            parent=None,
            position=None,
            tag="X1",
            description="Invented board",
        )
        parts_and_boards.extend([part, pcb, item])
    draft = Draft()
    draft.extend(parts_and_boards, origin=_CLASH_ORIGIN)
    return freeze(draft)


def test_a_deliberate_export_name_clash_raises(tmp_path):
    """`ExportNameClash` has no `.findings` (unlike `BuildErrors`): assert on its own text."""
    model = _clashing_boards_model()
    result = BuildResult(model=model, findings=())
    with pytest.raises(ExportNameClash) as excinfo:
        fr.write(result, tmp_path / "out")
    text = str(excinfo.value)
    assert "EXPORT_NAME_CLASH (error): two subjects both resolve to the export name" in text


def _two_units_of_one_release_with_clashing_documents():
    """Two `Unit` instances of one `UnitRelease`, each the subject of its own document (EN3).

    A unit's export prefix is its release's own name/version/revision, never the unit's own
    identity (`_subjects.export_prefix`), so both documents' PDF names collide even though the
    documents themselves are unrelated records: `_export_name_clash`'s `hint`-not-`None`
    branch ("keep one document per release").
    """
    release = UnitRelease(
        id=make_id(UnitRelease, ("unit_release", "shared-release", "1", "1")),
        key=("unit_release", "shared-release", "1", "1"),
        name="shared-release",
        version=1,
        revision=1,
        interface="1",
    )
    revision = Revision(
        id=make_id(Revision, ("shared-release", "revision", "1")),
        key=("shared-release", "revision", "1"),
        release=release.id,
        version=1,
        revision=1,
        date="2026-01-01",
        text="First release",
        created="XX",
    )
    records: list = [release, revision]
    for suffix in ("a", "b"):
        unit = Unit(
            id=make_id(Unit, (f"unit-{suffix}",)),
            key=(f"unit-{suffix}",),
            release=release.id,
            parent=None,
        )
        item = Item(
            id=make_id(Item, (f"unit-item-{suffix}",)),
            key=(f"unit-item-{suffix}",),
            part=None,
            parent=None,
            position=None,
            tag=f"U{suffix.upper()}",
            description="Invented unit",
            unit=unit.id,
        )
        document = Document(
            id=make_id(Document, (f"document-{suffix}",)),
            key=(f"document-{suffix}",),
            preset=DocumentPreset.CABINET_SCHEMATIC,
            location=None,
            item=None,
            unit=unit.id,
            add=(),
            remove=(PageKind.SCHEMATIC, PageKind.PLC_LIST, PageKind.TERMINAL_LIST, PageKind.BOM),
            cover="Invented cover text.",
            notes=None,
        )
        records.extend([unit, item, document])
    draft = Draft()
    draft.extend(records, origin=_CLASH_ORIGIN)
    return freeze(draft)


def test_a_deliberate_export_name_clash_of_two_units_in_one_release_raises(tmp_path):
    """The `hint`-not-`None` branch: two units of the SAME release, "keep one document" text."""
    model = _two_units_of_one_release_with_clashing_documents()
    result = BuildResult(model=model, findings=())
    with pytest.raises(ExportNameClash) as excinfo:
        fr.write(result, tmp_path / "out")
    text = str(excinfo.value)
    assert (
        "EXPORT_NAME_CLASH (error): two units, both instances of release 'shared-release', "
        "both export the file 'shared-release-v1.1.pdf'; keep one document per release."
    ) in text


# -- Determinism -------------------------------------------------------------------


def test_two_writes_of_one_result_give_byte_equal_files(demo_cabinet, tmp_path):
    result = BuildResult(model=demo_cabinet, findings=())
    first = fr.write(result, tmp_path / "out1")
    second = fr.write(result, tmp_path / "out2")
    assert {p.name for p in first} == {p.name for p in second}
    for path in first:
        twin = tmp_path / "out2" / path.name
        assert twin.read_bytes() == path.read_bytes()


_TEXT_SUFFIXES = {".csv", ".xml", ".md", ".json", ".html", ".txt"}


def test_every_text_export_has_no_bom_and_no_carriage_return(demo_cabinet, tmp_path):
    """Guide build.md: UTF-8, no byte order mark, `\\n` line ends, on every OS."""
    result = BuildResult(model=demo_cabinet, findings=())
    written = [p for p in fr.write(result, tmp_path / "out") if p.suffix in _TEXT_SUFFIXES]
    assert {".csv"} <= {p.suffix for p in written}  # examined: text exports really were written
    bad = [
        p.name
        for p in written
        if p.read_bytes().startswith(b"\xef\xbb\xbf") or b"\r" in p.read_bytes()
    ]
    assert bad == []


# -- F4: check ordering -------------------------------------------------------------


def test_check_orders_error_then_warning_then_info(demo_cabinet):
    subject = next(iter(demo_cabinet.tables["item"]))
    findings = (
        Finding(code="Z_INFO", severity=Severity.INFO, subjects=(subject,), message="z"),
        Finding(code="A_ERROR", severity=Severity.ERROR, subjects=(subject,), message="a"),
        Finding(code="M_WARNING", severity=Severity.WARNING, subjects=(subject,), message="m"),
    )
    result = BuildResult(model=demo_cabinet, findings=findings)
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
    (resolved,) = fr.check(result)
    assert f"{origin.file}:{origin.line}" in resolved.message


def test_check_calls_kicad_check_for_every_board():
    model = build_board_and_rack_model()
    result = BuildResult(model=model, findings=())
    findings = fr.check(result)
    assert findings == ()


def test_board_and_rack_model_has_no_layout_missing_finding():
    """D12/model-0039 can-fail proof: a real board-mounted `Function` is correctly excluded.

    `build_board_and_rack_model()` authors one `Function` directly on the board item
    (render work order PART 5b) and is never given a `layout.page` (it has no location to
    lay anything out at). Before model-0039, `LAYOUT_MISSING` fired on any non-empty
    `functions(model)`, so this model -- a genuine board/rack-only submission -- tripped a
    false-positive `ERROR` and would have blocked `fr.write` entirely. `schematic_functions`
    excludes the board's own function (the board exclusion covers its own leaf item, not
    only descendants'), so `LAYOUT_MISSING` must not fire even though the model genuinely
    holds a `Function` record and no `layout.page`.
    """
    model = build_board_and_rack_model()
    assert model.tables["function"]  # the board's own function: a non-vacuous can-fail base
    result = BuildResult(model=model, findings=())
    findings = fr.check(result)
    assert not any(f.code == "LAYOUT_MISSING" for f in findings)


def _model_with_an_unlaid_out_function():
    """A frozen model: one `Function`, no location, never run through `lay_out_schematic`.

    Carries a `SYSTEM` document (no subject) so `fr.check`'s PS1/PS2 gate (MODEL-BUILD, decision
    0037, "layout runs only on a model with a document") does not itself skip
    `fransys_render.check` here -- this test's own point is that `check` calls it at all, a
    fact this model's un-laid-out `Function` (never run through `lay_out_schematic`, so no
    `layout.page` exists for it) still proves once that gate is satisfied.
    """
    origin = Origin(file="packages/fransys/tests/test_acceptance.py", line=1, note="invented")
    item = Item(
        id=make_id(Item, ("item",)),
        key=("item",),
        part=None,
        parent=None,
        position=None,
        tag="Q1",
        description="Invented",
    )
    function = Function(
        id=make_id(Function, ("function",)),
        key=("function",),
        item=item.id,
        template=None,
        name="f",
        kind=FunctionKind.GENERIC,
    )
    draft = Draft()
    draft.extend([item, function, _system_document("unlaid-out-function")], origin=origin)
    return freeze(draft)


def test_check_calls_fransys_render_check_for_the_model():
    """F4: `check` calls `fransys_render.check`, not just `fransys_kicad`/`fransys_pdf`.

    A model with a `Function` but no `layout.page` (never run through `fr.build`) is exactly
    `fransys_render.check`'s own `LAYOUT_MISSING` case; `fr.check` must surface it, proving
    `_check` really calls `fransys_render.check(model)` and not just the other two.
    """
    model = _model_with_an_unlaid_out_function()
    result = BuildResult(model=model, findings=())
    findings = fr.check(result)
    assert len(findings) == 1
    assert findings[0].code == "LAYOUT_MISSING"
    assert findings[0].severity is Severity.ERROR


# -- F4/F5: SYMBOL_PORT_MISSING (examples gap G10, decision 0018) ---------------


_PART_FILE = "examples/demo-parts/demo_parts/parts/broken-relay.toml"
# The `[part]` header's own line: distinct from `_FUNCTION_ORIGIN` below, the way
# `fransys_parts.loader` gives a `Part` and its `FunctionTemplate`s different lines of
# one file, so a test can tell "the part file, the `Part`'s own line" apart from "the part
# file, that function's line" -- both fallbacks the finding's origin can resolve to.
_PART_HEADER_ORIGIN = Origin(file=_PART_FILE, line=3, note="invented")
_FUNCTION_ORIGIN = Origin(file=_PART_FILE, line=10, note="invented")
_DESIGN_ORIGIN = Origin(file="packages/fransys/tests/test_acceptance.py", line=1, note="invented")


def _system_document(name: str) -> Document:
    """A `SYSTEM` document (no subject): PS1/PS2's "layout runs only on a model with a
    document" gate (MODEL-BUILD, decision 0037) needs one before `fr.build` will call
    `lay_out_schematic` at all -- these `SymbolPortError` tests raise from inside that call,
    so without this the error never fires and `SYMBOL_PORT_MISSING` never appears. Removes
    every one of `SYSTEM`'s own default pages (`HARNESS_DRAWING`, `CABLE_LIST`, `BOM`) so
    `fransys_pdf.check` has nothing of its own to report empty on a model that holds none of
    that content (`_model_build_cover.py`'s own docstring: this shape adds no finding and
    changes no layout record, verified empirically).
    """
    key = ("document", name)
    return Document(
        id=make_id(Document, key),
        key=key,
        preset=DocumentPreset.SYSTEM,
        location=None,
        item=None,
        add=(),
        remove=(PageKind.HARNESS_DRAWING, PageKind.CABLE_LIST, PageKind.BOM),
        cover="Invented cover text.",
        notes=None,
    )


def _model_with_a_symbol_port_mismatch() -> tuple[Draft, Id, Id]:
    """A part whose one port name matches no symbol port: examples gap G10, decision 0018.

    `coil` is `DEFAULT_RULES`' own rule (`operating-device`, no `port_map`); its symbol has
    ports `in`/`out`, never `WRONG`. This function's `FunctionTemplate` declares one port
    template, `WRONG`, so its `Function` has no pole pair either (a pole pair needs two
    linked ports) and no `layout.symbol_choice` gives it a `port_map`: `resolve` cannot bind
    `WRONG` to anything, and raises `SymbolPortError`. `Part` carries `_PART_HEADER_ORIGIN`;
    `FunctionTemplate`/`PortTemplate` carry `_FUNCTION_ORIGIN`, a different line of the same
    part file; `Item`/`Function`/`Port` carry `_DESIGN_ORIGIN`, a different file -- so the
    finding's origin can be told apart from both the part's own less-precise origin and the
    model's design-file one.

    Returns:
        The draft, the `Part`'s id and the `PortTemplate`'s id.
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
        role=PortRole.GENERIC,
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
        role=PortRole.GENERIC,
    )

    draft = Draft()
    draft.add(part, origin=_PART_HEADER_ORIGIN)
    draft.extend([function_template, port_template], origin=_FUNCTION_ORIGIN)
    draft.extend(
        [item, function, port, _system_document("symbol-port-mismatch")], origin=_DESIGN_ORIGIN
    )
    return draft, part.id, port_template.id


def test_symbol_port_missing_becomes_one_error_finding():
    """PART 1 test (a): `fr.check` reports the raised `SymbolPortError` as one finding.

    Exactly one `SYMBOL_PORT_MISSING`, `ERROR`. Asserted twice: on `result.findings` (before
    `describe`), the raw `code`/`severity`/`message`/`subjects` are exact -- the message
    names the part's mpn, the port and the symbol key, and `subjects` is the `PortTemplate`,
    not the `Part` or anything design-side; on `fr.check(result)` (after `describe`), the
    resolved message carries the part file at the function's line (`_FUNCTION_ORIGIN`), not
    the part's own header line (`_PART_HEADER_ORIGIN`) or the design file (`_DESIGN_ORIGIN`).
    """
    draft, _part_id, port_template_id = _model_with_a_symbol_port_mismatch()
    result = fr.build(draft)

    raw = [f for f in result.findings if f.code == "SYMBOL_PORT_MISSING"]
    assert len(raw) == 1
    assert raw[0].severity is Severity.ERROR
    assert raw[0].subjects == (port_template_id,)
    assert raw[0].message == (
        "part 'DEMO-BROKEN-RLY': model port 'WRONG' has no port on symbol 'operating-device'"
    )

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
    with pytest.raises(BuildErrors) as excinfo:
        fr.write(result, out_dir)
    assert any(f.code == "SYMBOL_PORT_MISSING" for f in excinfo.value.findings)
    assert not out_dir.exists() or list(out_dir.iterdir()) == []


def _model_with_an_extra_port_symbol_mismatch() -> tuple[Draft, Id]:
    """A templated function's *extra* port -- one its `FunctionTemplate` never declares.

    Reachable: `check_part_conformance` (`packages/fransys-model/src/fransys_model/
    vocab/validators/part_conformance.py:97-102`) already names this shape --
    `ITEM_PART_MISMATCH`, "has port ..., which no port template declares" -- as one of its
    ordinary findings, not a `freeze()`-time refusal. Since decision 0028 that ERROR ends
    `fransys.build` before layout (spec F3), so the test hands the built model to
    `lay_out_schematic` itself to reach `resolve`. The `FunctionTemplate` declares one port,
    `in` (which would bind fine, by name, to `operating-device`'s own `in` port -- this test
    never needs to prove that): the `Function` carries only the *extra* port, `WRONG`,
    `template=None`, nothing `port_templates(model)` has an entry for. `resolve` cannot bind
    it either, and raises `SymbolPortError` naming it, with the `Part` as the fallback
    origin (`pipeline._symbol_port_missing_finding`'s middle branch: no matching
    `PortTemplate`, but the item's `Part` is known).

    Returns:
        The draft and the `Part`'s id.
    """
    part_key = ("part", "Demo", "DEMO-EXTRA-PORT-RLY")
    part = Part(
        id=make_id(Part, part_key),
        key=part_key,
        mpn="DEMO-EXTRA-PORT-RLY",
        manufacturer="Demo",
        description="Invented relay with an unmapped hand-added port",
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
    port_template_key = (*function_template_key, "port", "in")
    port_template = PortTemplate(
        id=make_id(PortTemplate, port_template_key),
        key=port_template_key,
        function=function_template.id,
        name="in",
        role=PortRole.GENERIC,
    )

    item = Item(
        id=make_id(Item, ("item", "k2")),
        key=("item", "k2"),
        part=part.id,
        parent=None,
        position=None,
        tag="K2",
        description="Invented",
    )
    function_key = ("function", "k2", "coil")
    function = Function(
        id=make_id(Function, function_key),
        key=function_key,
        item=item.id,
        template=function_template.id,
        name="coil",
        kind=FunctionKind.COIL,
    )
    # No `port_templates(model)` entry names `WRONG`; `template=None` on the instance itself
    # matches how a hand-added port (never run through `instantiate`) is authored.
    extra_port_key = (*function_key, "port", "WRONG")
    extra_port = Port(
        id=make_id(Port, extra_port_key),
        key=extra_port_key,
        function=function.id,
        template=None,
        name="WRONG",
        role=PortRole.GENERIC,
    )

    draft = Draft()
    draft.add(part, origin=_PART_HEADER_ORIGIN)
    draft.extend([function_template, port_template], origin=_FUNCTION_ORIGIN)
    draft.extend([item, function, extra_port], origin=_DESIGN_ORIGIN)
    return draft, part.id


def test_symbol_port_missing_falls_back_to_the_part_with_no_matching_port_template():
    """The extra-port case: no `PortTemplate` matches, so the origin falls back to the `Part`.

    The extra port fires `ITEM_PART_MISMATCH` (an `ERROR`), so `fr.build` runs no layout
    (decision 0028) and reports no `SYMBOL_PORT_MISSING`; the finding is built from the
    `SymbolPortError` that layout raises on that model, called directly.
    """
    draft, part_id = _model_with_an_extra_port_symbol_mismatch()
    result = fr.build(draft)

    assert any(f.code == "ITEM_PART_MISMATCH" for f in result.findings)
    assert not any(f.code == "SYMBOL_PORT_MISSING" for f in result.findings)
    with pytest.raises(SymbolPortError) as raised:
        lay_out_schematic(result.model)
    finding = _symbol_port_missing_finding(result.model, raised.value)
    assert finding.severity is Severity.ERROR
    assert finding.subjects == (part_id,)
    assert finding.message == (
        "part 'DEMO-EXTRA-PORT-RLY': model port 'WRONG' has no port on symbol 'operating-device'"
    )

    (resolved,) = _resolved((finding,), result.model)
    assert f"{_PART_HEADER_ORIGIN.file}:{_PART_HEADER_ORIGIN.line}" in resolved.message


def _model_with_a_part_less_symbol_mismatch() -> tuple[Draft, Id]:
    """A part-less item's function, authored directly, with a port matching no symbol port.

    Reachable: `fransys_model` design/vocabulary.md 7
    (`packages/fransys-model/docs/design/vocabulary.md:80`) documents this shape directly --
    "Items without a part (`part=None`) declare functions and ports directly. This is for early
    design; the `ITEM_WITHOUT_PART` finding (`INFO`) ... tracks them" -- not a refusal.
    `fransys_layout`'s own reading code (`_drawn.py:48`, `category =
    parts(model)[item.part].category.value if item.part is not None else None`) handles `item.part
    is None` by construction, and `derive.structure.schematic_functions` (`structure.py:230-234`)
    excludes a function only by its item's `part` sitting in the cable or board part sets -- `None`
    is in neither -- so a part-less item's function is drawn like any other. `resolve` still needs a
    real symbol match for it: `kind="coil"` reaches `DEFAULT_RULES`' `operating-device` rule the
    same way regardless of `part`, and a port named `WRONG` still binds nothing.
    `pipeline._symbol_port_missing_finding`'s innermost branch applies: no `Part` (so no
    `PortTemplate` search is even attempted) -- the origin falls back to the function itself.

    Returns:
        The draft and the `Function`'s id.
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
        role=PortRole.GENERIC,
    )

    draft = Draft()
    draft.extend(
        [item, function, port, _system_document("part-less-symbol-mismatch")],
        origin=_DESIGN_ORIGIN,
    )
    return draft, function.id


def test_symbol_port_missing_falls_back_to_the_function_with_no_part_at_all():
    """The part-less case: no `Part` and no `PortTemplate`, so the origin is the function.

    Also confirms the shape is real: `ITEM_WITHOUT_PART` fires alongside it (`INFO`, never
    blocking), and layout still runs and raises regardless.
    """
    draft, function_id = _model_with_a_part_less_symbol_mismatch()
    result = fr.build(draft)

    assert any(f.code == "ITEM_WITHOUT_PART" for f in result.findings)
    raw = [f for f in result.findings if f.code == "SYMBOL_PORT_MISSING"]
    assert len(raw) == 1
    assert raw[0].severity is Severity.ERROR
    assert raw[0].subjects == (function_id,)
    assert raw[0].message == (
        "part 'no part': model port 'WRONG' has no port on symbol 'operating-device'"
    )


# -- units spec U6 / root decision 0016: cables.csv, a system-only export -----------


def _model_with_a_unit_and_a_top_level_cable() -> tuple[Draft, Id]:
    """A one-item unit `U1` and one top-level (`unit=None`) cable `W1` with a single core.

    `cable_list_rows` (and so `cables_csv`) only ever returns `unit=None` cables by
    construction, so this fixture keeps the cable outside `unit`, the way units spec U3's
    "cable drawings" rule already treats a top-level cable -- there is no scoped-to-a-unit
    cable to build here. The core gives WireViz's `top_level_drawings` something to draw
    (a cable with zero cores raises inside `wireviz.Harness.add_cable`, not a shape this
    fixture needs to exercise).

    Returns:
        The draft, and `U1`'s own `Id[Unit]`.
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
        role=PortRole.GENERIC,
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
        role=PortRole.GENERIC,
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


def test_write_unit_none_includes_cables_csv_and_a_unit_write_excludes_it(tmp_path):
    """`cables.csv` is a system view, same as `overview.html` (units spec U6, decision 0016).

    `unit=None` writes it; `unit=<a real unit>` does not, on the same model -- a top-level
    cable and a unit-owned item both exist here, so the two cases are non-vacuous.
    """
    draft, unit_id = _model_with_a_unit_and_a_top_level_cable()
    result = fr.build(draft)

    whole = fr.write(result, tmp_path / "whole", unit=None)
    assert "cables.csv" in {p.name for p in whole}

    scoped = fr.write(result, tmp_path / "scoped", unit=unit_id)
    assert "cables.csv" not in {p.name for p in scoped}
    assert "overview.html" not in {p.name for p in scoped}  # the same system-view rule
