"""Facade `release` (baseline spec `docs/specs/2026-09-23-baseline.md`, L1, L3, L4).

Builds one small design once (root CLAUDE.md's speed-work rule, a module fixture): a board
unit with its own boundary connector and internal wiring (`_board_unit`, similar shape to the
units worked example's `io_board`), nested once inside a cabinet unit (`_cabinet_unit`), each
with its own document (`fr.document`, the unit itself as subject -- designer ruling LD6, since
a location inside a unit has no drawing of its own). L4's five checks
(`REVISION_ALREADY_RELEASED`, `RELEASE_NESTED_UNRELEASED`, `BASELINE_DIFFERS`,
`INTERFACE_NOT_BUMPED`, `RELEASE_NO_HISTORY`) are exercised below, each with a clean twin next
to its perturbed one; the perturbed twins skip documents entirely (`fr.build(parts,
design.draft())`, no `fr.document(...)` call) since `release`'s own L4 gate runs and raises
before `_exports` ever needs one -- a document is needed only where a test releases
successfully and checks the written tree.
"""

import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

import fransys as fr
import fransys_author
import pytest
from fransys_reports import changes_csv, changes_markdown

from fransys_model.derive import baseline, numbering_pins
from fransys_model.derive.unit_relative_key import unit_relative_key
from fransys_model.vocab import projects


def _board_unit(s, *, wire_colour="BU", revision=1, version=1):
    """A minimal board unit: one boundary connector (`X1`) with a relay (`K1`) wired to it."""
    u = s.unit("baseline-board", version=version, revision=revision, interface="1")
    u.revision(revision, date="2026-09-26", text=f"Revision {revision}", created="OJB")
    grp = u.group("BRD", "I/O board")
    board = u.item("DEMO-PCB-IO", name="board", group=grp)
    x1 = u.item("DEMO-CONN-2P", tag="X1", parent=board, group=grp)
    k1 = u.item("DEMO-RLY-2CO-24", name="k1", parent=board, group=grp)
    wire = u.wiring(colour=wire_colour, gauge="0.5")
    wire(x1["1"], k1.fn("coil")["A1"])
    wire(x1["2"], k1.fn("coil")["A2"])
    u.boundary(x1)
    return x1, u


def _cabinet_unit(s, *, name, wire_colour="BU"):
    """A cabinet unit nesting one board once, mated to a cabinet-side connector (`P1`)."""
    u = s.unit("baseline-cabinet", revision=1, interface="1")
    u.revision(1, date="2026-09-26", text="First release", created="OJB")
    c = u.location(name, "Cabinet")
    grp = u.group("FLD", "Field wiring")
    p1 = u.item("DEMO-CONN-2P", tag="P1", at=c, group=grp)
    board_x1, board_scope = _board_unit(u.scope("brd", at=c), wire_colour=wire_colour)
    u.mate(p1, board_x1)
    return u, board_scope


@pytest.fixture(scope="module")
def released(tmp_path_factory):
    """One build, released once per unit: the board, then the cabinet."""
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    cabinet_scope, board_scope = _cabinet_unit(design.scope("cab"), name="C1")

    covers = tmp_path_factory.mktemp("covers")
    board_cover = covers / "board.md"
    board_cover.write_text("# Board\n", encoding="utf-8")
    cabinet_cover = covers / "cabinet.md"
    cabinet_cover.write_text("# Cabinet\n", encoding="utf-8")
    board_doc = fr.document(fr.DocumentPreset.PCB_SCHEMATIC, board_scope, cover=board_cover)
    cabinet_doc = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC, cabinet_scope, cover=cabinet_cover
    )

    result = fr.build(parts, design.draft(), board_doc, cabinet_doc)
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors

    into = tmp_path_factory.mktemp("releases")
    board_target = fr.release(result, into, unit=board_scope)
    cabinet_target = fr.release(result, into, unit=cabinet_scope)
    return result, into, board_target, cabinet_target, board_scope, cabinet_scope


def _baseline_paths(target):
    baseline_dir = target / "baseline"
    return (
        baseline_dir / "listing.json",
        baseline_dir / "model.json",
        baseline_dir / "manifest.json",
    )


def _copy_into(tmp_path_factory, base_into):
    """A fresh copy of an already-released `into` tree, for a perturbed twin's own release."""
    into = tmp_path_factory.mktemp("into_copy")
    shutil.copytree(base_into, into, dirs_exist_ok=True)
    return into


def test_release_refuses_a_unit_of_the_wrong_type_and_writes_nothing(released, tmp_path_factory):
    """`fr.release`'s `unit=` resolution (`_resolve_unit`, shared with `write`): a value that
    is not `None`, a `Scope` with a unit, a unit `Id`, or a unit release name raises
    `TypeError` before any check or write runs, and `into` stays empty."""
    result, _into, _bt, _ct, _bs, _cs = released
    into = tmp_path_factory.mktemp("bad_unit_type")
    with pytest.raises(TypeError, match="unit="):
        fr.release(result, into, unit=42)
    assert list(into.iterdir()) == []


def test_release_writes_the_document_set_and_the_three_baseline_files(released):
    _result, _into, board_target, cabinet_target, _board_scope, _cabinet_scope = released
    for target in (board_target, cabinet_target):
        listing_path, model_path, manifest_path = _baseline_paths(target)
        assert listing_path.exists()
        assert model_path.exists()
        assert manifest_path.exists()
        assert list(target.glob("*.pdf")), f"{target} has no PDF"


def test_release_manifest_has_the_l3_shape(released):
    _result, _into, board_target, _cabinet_target, _board_scope, _cabinet_scope = released
    manifest = json.loads((board_target / "baseline" / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest) == {
        "listing_digest",
        "model_digest",
        "unit",
        "history",
        "packages",
        "part_libraries",
        "tool_versions",
        "warnings",
        "nested",
        "files",
    }
    assert manifest["unit"] == {
        "name": "baseline-board",
        "version": 1,
        "revision": 1,
        "interface": "1",
    }
    assert manifest["history"] == {
        "date": "2026-09-26",
        "text": "Revision 1",
        "created": "OJB",
        "checked": "",
        "approved": "",
    }
    assert len(manifest["packages"]) == 12
    assert {"name": "demo-parts", "version": "0.1.0"} in manifest["part_libraries"]
    assert set(manifest["tool_versions"]) == {"typst"}
    assert manifest["nested"] == []
    assert manifest["files"], "the board's own document set is listed"
    assert all({"path", "sha256"} == set(f) for f in manifest["files"])
    listing_bytes = (board_target / "baseline" / "listing.json").read_bytes()

    assert manifest["listing_digest"] == hashlib.sha256(listing_bytes).hexdigest()


def test_part_library_versions_skips_a_part_authored_in_python():
    """`_part_library_versions` (manifest `part_libraries`, L3): a `Part` with no `library` --
    `Part.library`'s own docstring: `None` for one "authored in Python", never sourced from a
    loaded part-file library, a shape `fransys_author` itself never produces today but the
    model schema allows and this reader must still handle -- contributes no entry, while a
    real, library-sourced part's does. Hand-built model (no `fr.build`/`fransys_author`, the same
    pattern `tests/test_units_worked_example.py`'s cross-unit probe uses): this is the only
    way to construct a `Part` with `library=None` at all.
    """
    from fransys._release_manifest import _part_library_versions

    from fransys_model.kernel import Draft, Origin, freeze, make_id
    from fransys_model.vocab.core import Item
    from fransys_model.vocab.enums import PartCategory
    from fransys_model.vocab.templates import Part, PartLibrary

    library_key = ("part_library", "demo-parts")
    library = PartLibrary(
        id=make_id(PartLibrary, library_key), key=library_key, name="demo-parts", version="0.1.0"
    )
    with_lib_key = ("part", "Demo", "WITH-LIB")
    with_lib = Part(
        id=make_id(Part, with_lib_key),
        key=with_lib_key,
        mpn="WITH-LIB",
        manufacturer="Demo",
        description="a library-sourced part",
        category=PartCategory.GENERIC,
        class_code="Z",
        library=library.id,
    )
    no_lib_key = ("part", "Demo", "NO-LIB")
    no_lib = Part(
        id=make_id(Part, no_lib_key),
        key=no_lib_key,
        mpn="NO-LIB",
        manufacturer="Demo",
        description="a part authored in Python, no library",
        category=PartCategory.GENERIC,
        class_code="Z",
        library=None,
    )
    with_lib_item_key = ("item", "z1")
    with_lib_item = Item(
        id=make_id(Item, with_lib_item_key),
        key=with_lib_item_key,
        part=with_lib.id,
        parent=None,
        position=None,
        tag="Z1",
        description="",
    )
    no_lib_item_key = ("item", "z2")
    no_lib_item = Item(
        id=make_id(Item, no_lib_item_key),
        key=no_lib_item_key,
        part=no_lib.id,
        parent=None,
        position=None,
        tag="Z2",
        description="",
    )
    draft = Draft()
    draft.extend(
        (library, with_lib, no_lib, with_lib_item, no_lib_item),
        origin=Origin(file="<probe>", line=1, note="Part.library=None"),
    )
    model = freeze(draft)

    assert _part_library_versions(model, None) == [{"name": "demo-parts", "version": "0.1.0"}]


def test_the_cabinets_manifest_names_the_nested_board_release(released):
    _result, _into, _board_target, cabinet_target, _board_scope, _cabinet_scope = released
    manifest = json.loads(
        (cabinet_target / "baseline" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["unit"]["name"] == "baseline-cabinet"
    assert [n["name"] for n in manifest["nested"]] == ["baseline-board"]


def test_release_again_unchanged_writes_nothing(released):
    result, into, board_target, cabinet_target, board_scope, cabinet_scope = released
    mtimes_before = {
        path: path.stat().st_mtime_ns
        for target in (board_target, cabinet_target)
        for path in target.rglob("*")
        if path.is_file()
    }
    assert mtimes_before, "the fixture's own releases wrote at least one file"

    returned_board = fr.release(result, into, unit=board_scope)
    returned_cabinet = fr.release(result, into, unit=cabinet_scope)
    assert returned_board == board_target
    assert returned_cabinet == cabinet_target

    mtimes_after = {
        path: path.stat().st_mtime_ns
        for target in (board_target, cabinet_target)
        for path in target.rglob("*")
        if path.is_file()
    }
    assert mtimes_before == mtimes_after

    for target in (board_target, cabinet_target):
        stray = [p.name for p in target.parent.iterdir() if p.name.startswith(".release-")]
        assert stray == [], f"the no-op path must never call mkdtemp under {target.parent}"


def test_two_releases_of_the_same_model_give_byte_equal_trees(released, tmp_path_factory):
    result, _into, _board_target, _cabinet_target, board_scope, cabinet_scope = released
    into_a = tmp_path_factory.mktemp("into_a")
    into_b = tmp_path_factory.mktemp("into_b")
    fr.release(result, into_a, unit=board_scope)
    fr.release(result, into_a, unit=cabinet_scope)
    fr.release(result, into_b, unit=board_scope)
    fr.release(result, into_b, unit=cabinet_scope)

    relative_a = sorted(path.relative_to(into_a) for path in into_a.rglob("*") if path.is_file())
    relative_b = sorted(path.relative_to(into_b) for path in into_b.rglob("*") if path.is_file())
    assert relative_a, "the fixture's own build writes at least one file"
    assert relative_a == relative_b
    for rel in relative_a:
        assert (into_a / rel).read_bytes() == (into_b / rel).read_bytes()


def test_release_atomicity_leaves_no_target_and_no_temp_dir_on_a_rename_failure(
    released, tmp_path_factory, monkeypatch
):
    """Can-fail (atomicity): every export and baseline file is written into the temporary
    directory for real; only the final atomic `Path.rename` is made to fail (monkeypatched),
    so this exercises `release`'s own `try`/`finally`/`shutil.rmtree` cleanup directly --
    unlike a probe that raises before `tempfile.mkdtemp` ever runs, which would pass
    vacuously (nothing was ever created to clean up). Leaves no target directory AND no
    stray `.release-*` temporary one either, on a fresh (never-before-released) target.
    """
    result, _into, _board_target, _cabinet_target, board_scope, _cabinet_scope = released
    into = tmp_path_factory.mktemp("fresh")

    def _boom(_self, *_args, **_kwargs):
        msg = "can-fail probe: forced rename failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(Path, "rename", _boom)
    with pytest.raises(RuntimeError, match="can-fail probe"):
        fr.release(result, into, unit=board_scope)

    parent = into / "baseline-board"
    target = parent / "1.1"
    assert not target.exists(), "the real target must not exist"
    stray = [p.name for p in parent.iterdir() if p.name.startswith(".release-")]
    assert stray == [], "no stray temporary directory either"


# -- L4: REVISION_ALREADY_RELEASED for the system release (unit=None) ------------------------
# Spec amended 2026-09-27: applies to the system exactly as to a unit (a released revision's
# folder never changes), with no subject to name (`subjects=()`, since there is no unit id).


def _system_result(*, extra_item):
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    design.project(
        title="Baseline system", number="P-BASELINE", customer="Demo", revision=1, author="OJB"
    )
    design.revision(1, date="2026-09-26", text="First issue", created="OJB")
    if extra_item:
        loc = design.location("SYS", "System")
        grp = design.group("SYS", "System")
        design.item("DEMO-CONN-2P", tag="Z1", at=loc, group=grp)
    result = fr.build(parts, design.draft())
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    return result


def test_releasing_the_system_twice_with_a_changed_listing_gives_revision_already_released(
    tmp_path_factory,
):
    into = tmp_path_factory.mktemp("system_release")
    first = _system_result(extra_item=False)
    target = fr.release(first, into)
    assert target == into / "P-BASELINE" / "1.1"
    mtimes_before = {p: p.stat().st_mtime_ns for p in target.rglob("*") if p.is_file()}
    assert mtimes_before, "the first, clean system release did write files"

    second = _system_result(extra_item=True)
    with pytest.raises(fr.BuildErrors) as exc:
        fr.release(second, into)
    codes = {f.code for f in exc.value.findings}
    assert codes == {"REVISION_ALREADY_RELEASED"}

    mtimes_after = {p: p.stat().st_mtime_ns for p in target.rglob("*") if p.is_file()}
    assert mtimes_before == mtimes_after, "the refused release must write nothing"
    stray = [p.name for p in target.parent.iterdir() if p.name.startswith(".release-")]
    assert stray == [], "no stray temporary directory either"


def test_releasing_the_system_twice_unchanged_is_a_no_op(tmp_path_factory):
    into = tmp_path_factory.mktemp("system_release_clean")
    result = _system_result(extra_item=False)
    target = fr.release(result, into)
    mtimes_before = {p: p.stat().st_mtime_ns for p in target.rglob("*") if p.is_file()}
    assert mtimes_before

    again = fr.release(result, into)
    assert again == target
    mtimes_after = {p: p.stat().st_mtime_ns for p in target.rglob("*") if p.is_file()}
    assert mtimes_before == mtimes_after


def test_manifest_warnings_render_a_non_item_subject_by_its_key_text(tmp_path_factory):
    """`_subject_text`'s fallback: a WARNING whose subject has no item/function/port reader
    (a declared `Net`'s own id, kind `net`) renders as the record's own authoring key
    (`kernel.key_text`), never the raw id (DESIGN 6: `Id` stays unexported). Only a SYSTEM
    release (`unit=None`) keeps a net-only-subject WARNING at all -- `_warning_entries` filters
    a real unit's own warnings down to its own item/function/port ids, and a net's id is none
    of those; see QUESTIONS AND THE CHOICE I MADE.
    """
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    design.project(
        title="Baseline system", number="P-NET-WARN", customer="Demo", revision=1, author="OJB"
    )
    design.revision(1, date="2026-09-26", text="First issue", created="OJB")
    loc = design.location("SYS", "System")
    grp = design.group("SYS", "System")
    p1 = design.item("DEMO-CONN-2P", tag="P1", at=loc, group=grp)
    p2 = design.item("DEMO-CONN-2P", tag="P2", at=loc, group=grp)
    design.net("unreal", p1["1"], p2["1"])  # never wired: two separate physical nets

    result = fr.build(parts, design.draft())
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    warnings = [f for f in fr.check(result) if f.severity is fr.Severity.WARNING]
    assert any(f.code == "NET_UNREALISED" for f in warnings), warnings

    into = tmp_path_factory.mktemp("net_warning")
    target = fr.release(result, into)
    manifest = json.loads((target / "baseline" / "manifest.json").read_text(encoding="utf-8"))
    net_warnings = [w for w in manifest["warnings"] if w["code"] == "NET_UNREALISED"]
    assert len(net_warnings) == 1
    assert net_warnings[0]["subjects"] == ["net/unreal"]


# -- L4: RELEASE_NESTED_UNRELEASED (cabinet released before its board) ----------------------


def test_releasing_the_cabinet_before_the_board_gives_release_nested_unreleased(
    released, tmp_path_factory
):
    """The clean twin is the fixture's own construction above (board, then cabinet, both
    succeed): not duplicated here.
    """
    result, _into, _board_target, _cabinet_target, _board_scope, cabinet_scope = released
    fresh_into = tmp_path_factory.mktemp("cabinet_first")
    with pytest.raises(fr.BuildErrors) as exc:
        fr.release(result, fresh_into, unit=cabinet_scope)
    codes = {f.code for f in exc.value.findings}
    assert codes == {"RELEASE_NESTED_UNRELEASED"}
    assert not (fresh_into / "baseline-cabinet").exists()


# -- L4: REVISION_ALREADY_RELEASED and BASELINE_DIFFERS (a board wire colour changes) --------


@pytest.fixture(scope="module")
def colour_twin(released, tmp_path_factory):
    """The base cabinet+board, rebuilt with the board's wire colour changed.

    Releasing into a copy of the base `into` exercises `REVISION_ALREADY_RELEASED` (the board
    itself, already released unchanged) and `BASELINE_DIFFERS` (the cabinet's own nested-board
    check) from the one perturbed build.
    """
    _result, base_into, _bt, _ct, _bs, _cs = released
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    cabinet_scope, board_scope = _cabinet_unit(design.scope("cab"), name="C1", wire_colour="BK")
    result = fr.build(parts, design.draft())
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors

    into = _copy_into(tmp_path_factory, base_into)
    return result, into, board_scope, cabinet_scope


def test_board_wire_colour_change_makes_the_board_revision_already_released(colour_twin):
    result, into, board_scope, _cabinet_scope = colour_twin
    with pytest.raises(fr.BuildErrors) as exc:
        fr.release(result, into, unit=board_scope)
    codes = {f.code for f in exc.value.findings}
    assert codes == {"REVISION_ALREADY_RELEASED"}
    (finding,) = exc.value.findings
    assert "conductors" in finding.message


def test_board_wire_colour_change_makes_the_cabinets_baseline_differ(colour_twin):
    result, into, _board_scope, cabinet_scope = colour_twin
    with pytest.raises(fr.BuildErrors) as exc:
        fr.release(result, into, unit=cabinet_scope)
    codes = {f.code for f in exc.value.findings}
    assert codes == {"BASELINE_DIFFERS"}
    (finding,) = exc.value.findings
    assert "conductors" in finding.message


# -- L4: REVISION_ALREADY_RELEASED naming `mates` (P1 mates a second board connector) --------


def _board_with_spare(s, *, unused):
    """Like `_board_unit`, plus a second boundary connector `X2` (the mate-swap scenario).

    `unused` names which connector ("X1" or "X2") has no real connection in this build and is
    declared `unused` (units spec U6, `d.unused(...)`'s own pattern in
    `test_units_worked_example.py`): the mate-swap probe below mates the cabinet's `P1` to
    whichever one is NOT named here.
    """
    u = s.unit("baseline-mate-board", revision=1, interface="1")
    u.revision(1, date="2026-09-26", text="First release", created="OJB")
    grp = u.group("BRD", "I/O board")
    board = u.item("DEMO-PCB-IO", name="board", group=grp)
    x1 = u.item("DEMO-CONN-2P", tag="X1", parent=board, group=grp)
    x2 = u.item("DEMO-CONN-2P", tag="X2", parent=board, group=grp)
    k1 = u.item("DEMO-RLY-2CO-24", name="k1", parent=board, group=grp)
    wire = u.wiring(colour="BU", gauge="0.5")
    wire(x1["1"], k1.fn("coil")["A1"])
    wire(x1["2"], k1.fn("coil")["A2"])
    u.boundary(x1)
    u.boundary(x2)
    u.unused(x2 if unused == "X2" else x1)
    return x1, x2, u


@pytest.fixture(scope="module")
def mate_scenario(tmp_path_factory):
    """A cabinet mating its `P1` to one of the board's two boundary connectors.

    The mate is a CABINET-level fact (Part 2's own LCA-scoping decision): the cabinet's own
    top-level digest changes when the mate target swaps, never a nested one, so the board's
    own release stays untouched by this scenario.
    """
    parts = fr.parts("demo_parts")

    def _build(*, mated):
        design = fransys_author.Design(parts)
        cab = design.scope("matecab").unit("baseline-mate-cabinet", revision=1, interface="1")
        cab.revision(1, date="2026-09-26", text="First release", created="OJB")
        c = cab.location("C1", "Cabinet")
        grp = cab.group("FLD", "Field wiring")
        p1 = cab.item("DEMO-CONN-2P", tag="P1", at=c, group=grp)
        unused = "X1" if mated == "X2" else "X2"
        x1, x2, board_scope = _board_with_spare(cab.scope("brd", at=c), unused=unused)
        cab.mate(p1, x2 if mated == "X2" else x1)
        result = fr.build(parts, design.draft())
        errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
        assert errors == [], errors
        return result, board_scope, cab

    clean_result, clean_board_scope, clean_cabinet_scope = _build(mated="X1")
    into = tmp_path_factory.mktemp("mate_releases")
    fr.release(clean_result, into, unit=clean_board_scope)
    fr.release(clean_result, into, unit=clean_cabinet_scope)

    perturbed_result, _perturbed_board_scope, perturbed_cabinet_scope = _build(mated="X2")
    return into, perturbed_result, perturbed_cabinet_scope


def test_mating_a_second_board_connector_makes_the_cabinet_revision_already_released(
    mate_scenario,
):
    into, result, cabinet_scope = mate_scenario
    with pytest.raises(fr.BuildErrors) as exc:
        fr.release(result, into, unit=cabinet_scope)
    codes = {f.code for f in exc.value.findings}
    assert codes == {"REVISION_ALREADY_RELEASED"}
    (finding,) = exc.value.findings
    assert "mates" in finding.message


# -- L4: INTERFACE_NOT_BUMPED and RELEASE_NO_HISTORY (a standalone board's own revisions) ----


def _build_interface_board(  # noqa: PLR0913 -- one keyword per release/scenario axis
    parts, *, version=1, revision, interface, with_spare, with_history=True
):
    """A standalone board (no cabinet), at `version`/`revision`/`interface`, optionally with a
    second, declared-unused boundary connector `X2` (`with_spare`) so a boundary change is
    possible without also changing the port set of `X1`, and optionally with no `Revision`
    history entry at all (`with_history=False`, the `RELEASE_NO_HISTORY` probe).
    """
    design = fransys_author.Design(parts)
    u = design.scope("ifc").unit(
        "baseline-interface-board", version=version, revision=revision, interface=interface
    )
    if with_history:
        u.revision(revision, date="2026-09-26", text=f"Revision {revision}", created="OJB")
    grp = u.group("BRD", "I/O board")
    board = u.item("DEMO-PCB-IO", name="board", group=grp)
    x1 = u.item("DEMO-CONN-2P", tag="X1", parent=board, group=grp)
    k1 = u.item("DEMO-RLY-2CO-24", name="k1", parent=board, group=grp)
    wire = u.wiring(colour="BU", gauge="0.5")
    wire(x1["1"], k1.fn("coil")["A1"])
    wire(x1["2"], k1.fn("coil")["A2"])
    u.boundary(x1)
    if with_spare:
        x2 = u.item("DEMO-CONN-2P", tag="X2", parent=board, group=grp)
        u.boundary(x2)
        u.unused(x2)
    result = fr.build(parts, design.draft())
    return result, u


@pytest.fixture(scope="module")
def interface_scenario(tmp_path_factory):
    """A standalone board, released once at revision 1 (`1.1`) with no second connector."""
    parts = fr.parts("demo_parts")
    base_result, base_scope = _build_interface_board(
        parts, revision=1, interface="1", with_spare=False
    )
    errors = [f for f in fr.check(base_result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    into = tmp_path_factory.mktemp("interface_base")
    fr.release(base_result, into, unit=base_scope)
    return parts, into


def test_bumping_the_board_without_bumping_interface_gives_interface_not_bumped(
    interface_scenario, tmp_path_factory
):
    parts, base_into = interface_scenario
    into = _copy_into(tmp_path_factory, base_into)
    result, scope = _build_interface_board(parts, revision=4, interface="1", with_spare=True)
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    with pytest.raises(fr.BuildErrors) as exc:
        fr.release(result, into, unit=scope)
    codes = {f.code for f in exc.value.findings}
    assert codes == {"INTERFACE_NOT_BUMPED"}
    (finding,) = exc.value.findings
    assert "1.1" in finding.message


def test_bumping_the_board_and_its_interface_releases_cleanly(interface_scenario, tmp_path_factory):
    parts, base_into = interface_scenario
    into = _copy_into(tmp_path_factory, base_into)
    result, scope = _build_interface_board(parts, revision=4, interface="3", with_spare=True)
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    target = fr.release(result, into, unit=scope)
    assert target.exists()
    assert (target / "baseline" / "listing.json").exists()


def test_a_renamed_sibling_folder_is_invisible_to_the_previous_release_lookup(
    interface_scenario, tmp_path_factory
):
    """`_previous_release_listing`'s revision-dir regex guard: a sibling folder that does not
    match `<version>.<revision>` -- here the base release's own `1.1` folder, renamed to look
    like a stray `.release-*` leftover -- is invisible to the lookup, never read as "the
    previous release". Without the guard the release below would instead find the renamed
    folder's stored listing (same interface, a different boundary) and raise
    `INTERFACE_NOT_BUMPED`; with it, releasing the new revision succeeds.
    """
    parts, base_into = interface_scenario
    into = _copy_into(tmp_path_factory, base_into)
    (into / "baseline-interface-board" / "1.1").rename(
        into / "baseline-interface-board" / ".release-stale"
    )
    result, scope = _build_interface_board(parts, revision=4, interface="1", with_spare=True)
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    target = fr.release(result, into, unit=scope)
    assert target.exists()


def test_an_empty_sibling_folder_is_skipped_not_read_by_the_previous_release_lookup(
    tmp_path_factory,
):
    """`_previous_release_listing`'s "no stored listing" guard: a sibling revision folder
    that exists (matches the regex) but holds no `baseline/listing.json` yet -- a
    half-finished or hand-placed folder -- is skipped rather than read, so the lookup neither
    crashes nor mistakes it for a real previous release.
    """
    parts = fr.parts("demo_parts")
    into = tmp_path_factory.mktemp("empty_sibling")
    (into / "baseline-interface-board" / "1.0").mkdir(parents=True)
    result, scope = _build_interface_board(parts, revision=1, interface="1", with_spare=False)
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    target = fr.release(result, into, unit=scope)
    assert target == into / "baseline-interface-board" / "1.1"


def test_removing_the_boards_revision_entry_gives_release_no_history(
    interface_scenario, tmp_path_factory
):
    """`check()` itself already reports `REVISION_CURRENT_MISSING` (model schema SC5) for a
    revision with no history entry, an `ERROR` unrelated to this test's own L4 subject; the
    can-fail probe here is `RELEASE_NO_HISTORY`'s own presence in the raised set, not the
    whole code set (`check`'s own gap is a separate, already-existing finding).
    """
    parts, base_into = interface_scenario
    into = _copy_into(tmp_path_factory, base_into)
    result, scope = _build_interface_board(
        parts, revision=4, interface="3", with_spare=True, with_history=False
    )
    with pytest.raises(fr.BuildErrors) as exc:
        fr.release(result, into, unit=scope)
    codes = {f.code for f in exc.value.findings}
    assert "RELEASE_NO_HISTORY" in codes


# -- L4: INTERFACE_NOT_BUMPED compares only against the PREVIOUS release (order appendix -----
# ruling 2: `derive.release_order`'s "highest (version, revision) pair below", never a scan of
# every on-disk sibling) ----------------------------------------------------------------------


def test_a_lower_version_released_after_a_higher_one_is_not_compared_against_it(
    tmp_path_factory,
):
    """Versions run in parallel (FD4): releasing `2.1` first, then `1.1` of the same unit,
    with the same interface and a genuinely different boundary, must NOT raise
    `INTERFACE_NOT_BUMPED` -- `2.1` sorts ABOVE `1.1` (`release_order((2, 1)) > release_order((1,
    1))`), so it is never "the previous release below" `1.1`, and `1.1` has no other sibling
    to compare against at all. Scanning every sibling regardless of order (the pre-ruling
    behaviour) would incorrectly compare `1.1` against `2.1` and raise; this is CAN-FAIL's own
    probe below.
    """
    parts = fr.parts("demo_parts")
    into = tmp_path_factory.mktemp("previous_release_only")

    higher_result, higher_scope = _build_interface_board(
        parts, version=2, revision=1, interface="1", with_spare=False
    )
    errors = [f for f in fr.check(higher_result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    higher_target = fr.release(higher_result, into, unit=higher_scope)

    lower_result, lower_scope = _build_interface_board(
        parts, version=1, revision=1, interface="1", with_spare=True
    )
    errors = [f for f in fr.check(lower_result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    lower_target = fr.release(lower_result, into, unit=lower_scope)

    assert higher_target.exists()
    assert lower_target.exists()
    assert higher_target != lower_target


# -- L4: INTERFACE_NOT_BUMPED reads a boundary rating too (owner ruling 3, 2026-09-26) -------


def _build_rating_board(parts, *, revision, wire_colour="BU", rating=None):
    """A standalone board at `revision`, `X1`'s boundary stating `rating` (`None` by default)."""
    design = fransys_author.Design(parts)
    u = design.scope("rtg").unit("baseline-rating-board", revision=revision, interface="1")
    u.revision(revision, date="2026-09-26", text=f"Revision {revision}", created="OJB")
    grp = u.group("BRD", "I/O board")
    board = u.item("DEMO-PCB-IO", name="board", group=grp)
    x1 = u.item("DEMO-CONN-2P", tag="X1", parent=board, group=grp)
    k1 = u.item("DEMO-RLY-2CO-24", name="k1", parent=board, group=grp)
    wire = u.wiring(colour=wire_colour, gauge="0.5")
    wire(x1["1"], k1.fn("coil")["A1"])
    wire(x1["2"], k1.fn("coil")["A2"])
    u.boundary(x1, rating=rating)
    result = fr.build(parts, design.draft())
    return result, u


@pytest.fixture(scope="module")
def rating_scenario(tmp_path_factory):
    """A standalone board, released once at revision 1 with no boundary rating stated."""
    parts = fr.parts("demo_parts")
    base_result, base_scope = _build_rating_board(parts, revision=1)
    errors = [f for f in fr.check(base_result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    into = tmp_path_factory.mktemp("rating_base")
    fr.release(base_result, into, unit=base_scope)
    return parts, into


def test_a_new_revision_with_the_same_boundary_releases_cleanly(rating_scenario, tmp_path_factory):
    """The clean twin: an internal-only change (wire colour), same boundary, same interface,
    never trips `INTERFACE_NOT_BUMPED` -- the discriminating half of the probe below.
    """
    parts, base_into = rating_scenario
    into = _copy_into(tmp_path_factory, base_into)
    result, scope = _build_rating_board(parts, revision=2, wire_colour="BK")
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    target = fr.release(result, into, unit=scope)
    assert target.exists()


def test_a_boundary_rating_change_alone_gives_interface_not_bumped(
    rating_scenario, tmp_path_factory
):
    """Owner ruling 3 (2026-09-26): a boundary rating counts as part of the `boundary` section
    for `INTERFACE_NOT_BUMPED`'s comparison, even with the port set and connector unchanged --
    a version of the check that compared only `(designation, ports)` would miss this and pass
    vacuously (verified by hand: with `_interface_not_bumped_findings`'s boundary compare
    temporarily narrowed to `(designation, ports)` only, this test fails; reverted, it
    passes).
    """
    parts, base_into = rating_scenario
    into = _copy_into(tmp_path_factory, base_into)
    rating = fransys_author.Rating(voltage_dc_v=Decimal(24))
    result, scope = _build_rating_board(parts, revision=3, rating=rating)
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    with pytest.raises(fr.BuildErrors) as exc:
        fr.release(result, into, unit=scope)
    codes = {f.code for f in exc.value.findings}
    assert codes == {"INTERFACE_NOT_BUMPED"}


# -- L4: BASELINE_DIFFERS names the board two levels down, not the module in between ---------


def _module_unit(s, *, wire_colour="BU"):
    """A module unit with one own item (a carrier), nesting the board one level deeper.

    `_nested_unit_rows`'s own `min(...)` over `unit_own_roots` needs at least one item of the
    module's own to name an instance, so the module owns a small part-less carrier item
    beside the board it nests (advisor-flagged gap, fixed here). The module also declares the
    board's own `X1` its own boundary too (`UNIT_BOUNDARY_BYPASSED`, units spec U4: a function
    that crosses out of an intermediate unit must be that unit's own boundary as well, not
    only the innermost one's), so the cabinet's mate to `X1` can cross both unit walls.
    """
    u = s.unit("baseline-module", revision=1, interface="1")
    u.revision(1, date="2026-09-26", text="First release", created="OJB")
    grp = u.group("MOD", "Module")
    u.item(None, tag="MOD1", group=grp)
    board_x1, board_scope = _board_unit(u.scope("brd"), wire_colour=wire_colour)
    u.boundary(board_x1)
    return u, board_x1, board_scope


@pytest.fixture(scope="module")
def two_level_scenario(tmp_path_factory):
    """Board nested in a module nested in a cabinet (spec step 3's own two-level case).

    Releasing the cabinet after an inner board change gives `BASELINE_DIFFERS` naming the
    board itself, though the module's own listing (which names the board only by name,
    version and revision, never its internal wiring) stays equal.
    """
    parts = fr.parts("demo_parts")

    def _build(*, wire_colour):
        design = fransys_author.Design(parts)
        cab = design.scope("deep").unit("baseline-deep-cabinet", revision=1, interface="1")
        cab.revision(1, date="2026-09-26", text="First release", created="OJB")
        c = cab.location("C1", "Cabinet")
        grp = cab.group("FLD", "Field wiring")
        p1 = cab.item("DEMO-CONN-2P", tag="P1", at=c, group=grp)
        module_scope, board_x1, board_scope = _module_unit(
            cab.scope("mod", at=c), wire_colour=wire_colour
        )
        cab.mate(p1, board_x1)
        result = fr.build(parts, design.draft())
        errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
        assert errors == [], errors
        return result, board_scope, module_scope, cab

    clean_result, clean_board_scope, clean_module_scope, clean_cabinet_scope = _build(
        wire_colour="BU"
    )
    into = tmp_path_factory.mktemp("deep_releases")
    fr.release(clean_result, into, unit=clean_board_scope)
    fr.release(clean_result, into, unit=clean_module_scope)
    fr.release(clean_result, into, unit=clean_cabinet_scope)

    perturbed_result, perturbed_board_scope, _perturbed_module_scope, perturbed_cabinet_scope = (
        _build(wire_colour="BK")
    )
    return into, perturbed_board_scope, perturbed_cabinet_scope, perturbed_result


def test_a_deep_board_change_gives_baseline_differs_for_the_board_not_the_module(
    two_level_scenario,
):
    into, perturbed_board_scope, perturbed_cabinet_scope, perturbed_result = two_level_scenario
    with pytest.raises(fr.BuildErrors) as exc:
        fr.release(perturbed_result, into, unit=perturbed_cabinet_scope)
    findings = exc.value.findings
    codes = {f.code for f in findings}
    assert codes == {"BASELINE_DIFFERS"}
    (finding,) = findings
    assert finding.subjects == (perturbed_board_scope.unit_id,)


# -- FD5/FD6: DESIGNATION_MOVED (fixed-designations spec, Part 3) ----------------------------
# `_pin_source`/`_designation_moved_findings` (pipeline.py) and `_designation_pins.py`'s pure
# joins over two `NumberingPins`. No document is authored in any of these fixtures (`release`
# needs none): the point is the numbering pins alone.


def _relay_board(parts, *, revision, coil_b, aux, releases=None):
    """A standalone unit with free-numbered relays (spec's own worked example): `coil-a`
    always present; `coil-b`/`aux` each present only when asked. All three share one class
    code (`K`, `DEMO-RLY-2CO-24`), so free numbering counts them together in `(key, id)` order
    -- `aux` sorts before `coil-a` sorts before `coil-b`. `releases`, when given, is passed
    straight through to `fr.build` (Part 4's own seeding).
    """
    design = fransys_author.Design(parts)
    u = design.scope("rb").unit("relay-board", revision=revision, interface="1")
    u.revision(revision, date="2026-09-26", text=f"Revision {revision}", created="OJB")
    if aux:
        u.item("DEMO-RLY-2CO-24", name="aux")
    u.item("DEMO-RLY-2CO-24", name="coil-a")
    if coil_b:
        u.item("DEMO-RLY-2CO-24", name="coil-b")
    result = fr.build(parts, design.draft(), releases=releases)
    return result, u


def test_the_worked_examples_free_numbering_moves_coil_a_and_gives_designation_moved(
    tmp_path_factory,
):
    """The fixed-designations spec's own worked example: releasing `relay-board` `1.1` with
    `coil-a`/`coil-b` free-numbers them `coil-a` -> `K1`, `coil-b` -> `K2` (alphabetical `(key,
    id)` order, `passes.numbering.number`'s own rule). Revision `1.2` drops `coil-b` and adds
    `aux` (whose key sorts first): free numbering now gives `aux` -> `K1`, `coil-a` -> `K2` --
    `coil-a` itself never changed, but its printed number moved, which `DESIGNATION_MOVED`
    must catch even with no seeding at all (Part 3 alone, per the work order).
    """
    parts = fr.parts("demo_parts")
    into = tmp_path_factory.mktemp("relay_worked_example")

    result_v1, u_v1 = _relay_board(parts, revision=1, coil_b=True, aux=False)
    errors = [f for f in fr.check(result_v1) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    target_v1 = fr.release(result_v1, into, unit=u_v1)
    numbering_v1 = json.loads(
        (target_v1 / "baseline" / "numbering.json").read_text(encoding="utf-8")
    )
    by_last_segment_v1 = {row["key"][-1]: row["text"] for row in numbering_v1["items"]}
    assert by_last_segment_v1["coil-a"] == "K1"
    assert by_last_segment_v1["coil-b"] == "K2"

    result_v2, u_v2 = _relay_board(parts, revision=2, coil_b=False, aux=True)
    errors = [f for f in fr.check(result_v2) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    with pytest.raises(fr.BuildErrors) as exc:
        fr.release(result_v2, into, unit=u_v2)
    codes = {f.code for f in exc.value.findings}
    assert "DESIGNATION_MOVED" in codes
    (finding,) = [f for f in exc.value.findings if f.code == "DESIGNATION_MOVED"]
    assert "K1" in finding.message
    assert "K2" in finding.message


def test_two_releases_and_a_standalone_build_give_byte_equal_numbering(released, tmp_path_factory):
    """FD3/FD5 (Part 3 acceptance 2): two releases of one build, plus a wholly separate build
    of the same design, give byte-equal `baseline/numbering.json` for the board and the
    cabinet -- the same determinism `test_two_releases_of_the_same_model_give_byte_equal_trees`
    already proves for `listing.json`, extended to the new numbering file.
    """
    result, _into, _bt, _ct, board_scope, cabinet_scope = released
    into_a = tmp_path_factory.mktemp("numbering_a")
    into_b = tmp_path_factory.mktemp("numbering_b")
    fr.release(result, into_a, unit=board_scope)
    fr.release(result, into_a, unit=cabinet_scope)
    fr.release(result, into_b, unit=board_scope)
    fr.release(result, into_b, unit=cabinet_scope)

    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    standalone_cabinet_scope, standalone_board_scope = _cabinet_unit(design.scope("cab"), name="C1")
    standalone_result = fr.build(parts, design.draft())
    errors = [f for f in fr.check(standalone_result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    into_c = tmp_path_factory.mktemp("numbering_c")
    fr.release(standalone_result, into_c, unit=standalone_board_scope)
    fr.release(standalone_result, into_c, unit=standalone_cabinet_scope)

    for name, into_set in (
        ("baseline-board", (into_a, into_b, into_c)),
        ("baseline-cabinet", (into_a, into_b, into_c)),
    ):
        texts = {
            (into / name / "1.1" / "baseline" / "numbering.json").read_bytes() for into in into_set
        }
        assert len(texts) == 1, f"{name}'s numbering.json differs across builds"


def _tagged_relay(parts, *, revision, tag):
    """A standalone unit with one relay named `coil`, its own tag authored directly."""
    design = fransys_author.Design(parts)
    u = design.scope("tag").unit("tagged-relay-unit", revision=revision, interface="1")
    u.revision(revision, date="2026-09-26", text=f"Revision {revision}", created="OJB")
    u.item("DEMO-RLY-2CO-24", name="coil", tag=tag)
    result = fr.build(parts, design.draft())
    return result, u


def test_a_changed_authored_tag_between_two_releases_gives_designation_moved(tmp_path_factory):
    """Acceptance 6: the item itself is unchanged (same key, same part) between the two
    releases -- only its AUTHORED tag changes, `K1` to `K5`. `DESIGNATION_MOVED` fires exactly
    as it does for a free-numbered move.
    """
    parts = fr.parts("demo_parts")
    into = tmp_path_factory.mktemp("tagged_relay")

    result_v1, u_v1 = _tagged_relay(parts, revision=1, tag="K1")
    errors = [f for f in fr.check(result_v1) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    fr.release(result_v1, into, unit=u_v1)

    result_v2, u_v2 = _tagged_relay(parts, revision=2, tag="K5")
    errors = [f for f in fr.check(result_v2) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    with pytest.raises(fr.BuildErrors) as exc:
        fr.release(result_v2, into, unit=u_v2)
    codes = {f.code for f in exc.value.findings}
    assert "DESIGNATION_MOVED" in codes


def _partless_tagged_item(parts, *, revision, tag):
    """A standalone unit with one part-less, tagged item (`item.part = None`, a structural
    harness stand-in, `_module_unit`'s own `u.item(None, tag=...)` pattern): FD6's own words,
    "a board or harness whose own text changes shows on its own pin."
    """
    design = fransys_author.Design(parts)
    u = design.scope("hns").unit("partless-harness-unit", revision=revision, interface="1")
    u.revision(revision, date="2026-09-26", text=f"Revision {revision}", created="OJB")
    u.item(None, name="hns", tag=tag)
    result = fr.build(parts, design.draft())
    return result, u


def test_a_partless_tagged_items_changed_tag_gives_designation_moved(tmp_path_factory):
    """A part-less item's own tag counts too (`code=None` in its `NumberingItem`, per the
    2026-09-27 designer ruling): `numbering_pins.pins` includes it, so its tag change between
    two releases is caught the same as a part-carrying item's.
    """
    parts = fr.parts("demo_parts")
    into = tmp_path_factory.mktemp("partless_harness")

    result_v1, u_v1 = _partless_tagged_item(parts, revision=1, tag="W1")
    errors = [f for f in fr.check(result_v1) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    fr.release(result_v1, into, unit=u_v1)

    result_v2, u_v2 = _partless_tagged_item(parts, revision=2, tag="W5")
    errors = [f for f in fr.check(result_v2) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    with pytest.raises(fr.BuildErrors) as exc:
        fr.release(result_v2, into, unit=u_v2)
    codes = {f.code for f in exc.value.findings}
    assert "DESIGNATION_MOVED" in codes


def test_a_retirement_carries_forward_to_the_next_release(tmp_path_factory):
    """FD5's `retired` carry-forward (`_designation_pins.gone_or_moved`): once `coil-b`'s own
    designation retires at revision `1.2` (it is dropped from `relay-board`), the NEXT release,
    `1.3`, still lists it in `baseline/numbering.json`'s own `retired` even though nothing
    changes between `1.2` and `1.3` -- `gone_or_moved` must fold the pin source's own `retired`
    in, not only what newly goes missing this time. CAN-FAIL below breaks exactly this fold.
    """
    parts = fr.parts("demo_parts")
    into = tmp_path_factory.mktemp("retirement_carry_forward")

    result_v1, u_v1 = _relay_board(parts, revision=1, coil_b=True, aux=False)
    errors = [f for f in fr.check(result_v1) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    fr.release(result_v1, into, unit=u_v1)

    result_v2, u_v2 = _relay_board(parts, revision=2, coil_b=False, aux=False)
    errors = [f for f in fr.check(result_v2) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    fr.release(result_v2, into, unit=u_v2)

    result_v3, u_v3 = _relay_board(parts, revision=3, coil_b=False, aux=False)
    errors = [f for f in fr.check(result_v3) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    fr.release(result_v3, into, unit=u_v3)

    numbering_v3 = json.loads(
        (into / "relay-board" / "1.3" / "baseline" / "numbering.json").read_text(encoding="utf-8")
    )
    retired_texts = {entry["text"] for entry in numbering_v3["retired"]}
    assert "K2" in retired_texts, "coil-b's own retired text must carry forward to 1.3"


def _board_with_nested_relay(parts, *, revision, board_tag):
    """A board with a STABLE key (its own `name=`) but an authored tag that changes, nesting
    one relay whose own tag never changes and whose key does not move (same `scope`).
    """
    design = fransys_author.Design(parts)
    u = design.scope("nb").unit("nested-board-unit", revision=revision, interface="1")
    u.revision(revision, date="2026-09-26", text=f"Revision {revision}", created="OJB")
    board = u.item("DEMO-PCB-IO", name="board", tag=board_tag)
    u.item("DEMO-RLY-2CO-24", tag="K1", parent=board)
    result = fr.build(parts, design.draft())
    return result, u


def test_a_changed_ancestor_label_gives_designation_moved_only_for_the_ancestor(
    tmp_path_factory,
):
    """FD6's comparison is the item's OWN label (`NumberingItem.text`), never the full
    `item_designation` chain: renaming the enclosing board's own tag between two releases (a
    real move for the BOARD's own pin) while the nested relay's own tag stays `K1` must give
    exactly one `DESIGNATION_MOVED`, for the board alone -- the relay's own printed text never
    moved, only its ancestor's. CAN-FAIL below: with the comparison swapped to include the
    full chain, the relay wrongly gets flagged too (a second, spurious move).
    """
    parts = fr.parts("demo_parts")
    into = tmp_path_factory.mktemp("ancestor_label_change")

    result_v1, u_v1 = _board_with_nested_relay(parts, revision=1, board_tag="B1")
    errors = [f for f in fr.check(result_v1) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    fr.release(result_v1, into, unit=u_v1)

    result_v2, u_v2 = _board_with_nested_relay(parts, revision=2, board_tag="B2")
    errors = [f for f in fr.check(result_v2) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    with pytest.raises(fr.BuildErrors) as exc:
        fr.release(result_v2, into, unit=u_v2)
    moved = [f for f in exc.value.findings if f.code == "DESIGNATION_MOVED"]
    assert len(moved) == 1, "only the board's own pin moved, never the relay's"
    (finding,) = moved
    assert "B1" in finding.message
    assert "B2" in finding.message


def _mixed_partless_and_coded(parts, *, revision, keep_both):
    """A unit with a part-less tagged item (`code=None`) AND a class-coded one, either or both
    retired depending on `keep_both` -- proves `gone_or_moved`'s carry-forward sort tolerates
    a `NumberingRetired.code` of `None` alongside a real class code in the SAME list (a `str`
    vs `None` comparison, caught only by mixing the two in one release, review-caught: no
    existing fixture combined them).
    """
    design = fransys_author.Design(parts)
    u = design.scope("mix").unit("mixed-partless-unit", revision=revision, interface="1")
    u.revision(revision, date="2026-09-26", text=f"Revision {revision}", created="OJB")
    if keep_both:
        u.item(None, name="hns", tag="W1")
        u.item("DEMO-RLY-2CO-24", name="coil", tag="K1")
    else:
        u.item("DEMO-RLY-2CO-24", name="only-survivor", tag="K9")
    result = fr.build(parts, design.draft())
    return result, u


def test_retiring_a_part_less_and_a_coded_item_together_does_not_crash_the_sort(
    tmp_path_factory,
):
    """CAN-FAIL: before `_designation_pins.gone_or_moved`'s sort key guarded `code is None`
    the same way it guards `scope is None`, this raised `TypeError` (`'<' not supported
    between instances of 'str' and 'NoneType'`) the moment one release's `retired` list held
    both a part-less entry (`code=None`) and a coded one (`code="K"`) -- exactly this scenario.
    """
    parts = fr.parts("demo_parts")
    into = tmp_path_factory.mktemp("mixed_partless_retirement")

    result_v1, u_v1 = _mixed_partless_and_coded(parts, revision=1, keep_both=True)
    errors = [f for f in fr.check(result_v1) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    fr.release(result_v1, into, unit=u_v1)

    result_v2, u_v2 = _mixed_partless_and_coded(parts, revision=2, keep_both=False)
    errors = [f for f in fr.check(result_v2) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    # Both `hns` and `coil` are simply gone (not moved) in v2: no `DESIGNATION_MOVED`, and this
    # call must not raise `TypeError` either -- the point of this test. `gone_or_moved` runs
    # inside `release()` itself (writing `baseline/numbering.json`), regardless of any L4
    # finding, so a crash there would surface here even with a clean release.
    target_v2 = fr.release(result_v2, into, unit=u_v2)

    numbering_v2 = json.loads(
        (target_v2 / "baseline" / "numbering.json").read_text(encoding="utf-8")
    )
    retired_texts = {entry["text"] for entry in numbering_v2["retired"]}
    assert retired_texts == {"W1", "K1"}


# -- FD5: fr.build(releases=) seeding (fixed-designations spec, Part 4) ----------------------


def test_the_worked_example_with_releases_keeps_coil_as_number_and_reserves_coil_bs(
    tmp_path_factory,
):
    """Acceptance 1/2/9: with `releases=` at BUILD time, `coil-a` keeps `K1` across the
    revision that drops `coil-b` and adds `aux`, and `aux` gets `K3` (not `K2`, `coil-b`'s
    retired number) -- both FD1's no-reuse and FD5's own seeding, together. The v1.2 release
    succeeds with no `DESIGNATION_MOVED` (the seeding is exactly what makes that true; compare
    the un-seeded worked example above, which raises it).
    """
    parts = fr.parts("demo_parts")
    into = tmp_path_factory.mktemp("relay_worked_example_seeded")

    result_v1, u_v1 = _relay_board(parts, revision=1, coil_b=True, aux=False)
    errors = [f for f in fr.check(result_v1) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    fr.release(result_v1, into, unit=u_v1)

    result_v2, u_v2 = _relay_board(parts, revision=2, coil_b=False, aux=True, releases=into)
    errors = [f for f in fr.check(result_v2) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    pins_v2 = numbering_pins.pins(result_v2.model, u_v2.unit_id)
    by_last_segment = {row.key[-1]: row.text for row in pins_v2.items}
    assert by_last_segment["coil-a"] == "K1", "coil-a's pinned number must survive the reshuffle"
    assert by_last_segment["aux"] == "K3", "aux must skip both K1 (pinned) and K2 (reserved)"

    target_v2 = fr.release(result_v2, into, unit=u_v2)
    assert target_v2.exists()


def _movable_relay(parts, *, revision, under_board2):
    """A unit with two boards and one relay of a stable key, nested under whichever board
    `under_board2` names -- acceptance 4's own scenario: the relay's identity (`unit_relative_
    key`) never changes, only its designating ancestor.
    """
    design = fransys_author.Design(parts)
    u = design.scope("mv").unit("movable-unit", revision=revision, interface="1")
    u.revision(revision, date="2026-09-26", text=f"Revision {revision}", created="OJB")
    board1 = u.item("DEMO-PCB-IO", name="board1")
    board2 = u.item("DEMO-PCB-IO", name="board2")
    u.item("DEMO-RLY-2CO-24", name="relay", parent=board2 if under_board2 else board1)
    result = fr.build(parts, design.draft())
    return result, u


def test_an_item_moved_to_another_board_takes_a_new_number_and_reserves_the_old_one(
    tmp_path_factory,
):
    """Acceptance 4: `relay` moves from `board1` to `board2` between two revisions. Free
    numbering alone would give it `K1` in board2's group regardless (board2 has no other
    class-K item), so the real proof is in the pin file: `board1`'s old pin (`K1`, `scope`
    board1's relative key) is RESERVED, not silently dropped, and no `DESIGNATION_MOVED` fires
    (the relay's own printed text, `K1`, happens to stay the same; the RELEASE's own SCOPE
    changed, which is exactly why FD6 does not compare on the bare text alone across a move --
    it never even reaches the seeded/current pair, since seeding only applies where scope AND
    code both still match).
    """
    parts = fr.parts("demo_parts")
    into = tmp_path_factory.mktemp("movable_relay")

    result_v1, u_v1 = _movable_relay(parts, revision=1, under_board2=False)
    errors = [f for f in fr.check(result_v1) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    fr.release(result_v1, into, unit=u_v1)

    design = fransys_author.Design(parts)
    u_v2 = design.scope("mv").unit("movable-unit", revision=2, interface="1")
    u_v2.revision(2, date="2026-09-26", text="Revision 2", created="OJB")
    board1 = u_v2.item("DEMO-PCB-IO", name="board1")
    board2 = u_v2.item("DEMO-PCB-IO", name="board2")
    u_v2.item("DEMO-RLY-2CO-24", name="relay", parent=board2)
    result_v2 = fr.build(parts, design.draft(), releases=into)
    errors = [f for f in fr.check(result_v2) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    # board1/board2 are top-level items of the unit's own scope: each one's own relative key
    # is simply its own name, one plain segment, with no further ancestor board of its own.
    assert unit_relative_key(result_v2.model, board1.id) == ("board1",)
    assert unit_relative_key(result_v2.model, board2.id) == ("board2",)

    target_v2 = fr.release(result_v2, into, unit=u_v2)
    numbering_v2 = json.loads(
        (target_v2 / "baseline" / "numbering.json").read_text(encoding="utf-8")
    )
    by_key = {tuple(row["key"]): row for row in numbering_v2["items"]}
    assert by_key[("relay",)]["scope"] == ["board2"], "relay's pin now names its NEW board"
    retired_scopes = {
        (entry["scope"] and tuple(entry["scope"]), entry["text"])
        for entry in numbering_v2["retired"]
    }
    assert ((("board1",), "K1")) in retired_scopes, "board1's old K1 pin must be reserved"


def test_version_2s_first_release_seeds_no_pins_from_version_1(tmp_path_factory):
    """Acceptance 5: version 2 starts again at revision 1, free-numbered -- `same_version`'s
    filter (already proven at the release-order level by BASELINE-WRITER/FD4) means
    `_pin_source` finds nothing for `(name, version=2, revision=1)` even though `1.1` of the
    same name is already released, so seeding never runs and version 2 numbers exactly as an
    un-pinned build would.
    """
    parts = fr.parts("demo_parts")
    into = tmp_path_factory.mktemp("version_seeding")

    result_v1, u_v1 = _relay_board(parts, revision=1, coil_b=True, aux=False)
    errors = [f for f in fr.check(result_v1) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    fr.release(result_v1, into, unit=u_v1)

    design = fransys_author.Design(parts)
    u_v2 = design.scope("rb2").unit("relay-board", version=2, revision=1, interface="1")
    u_v2.revision(1, version=2, date="2026-09-26", text="First v2 release", created="OJB")
    u_v2.item("DEMO-RLY-2CO-24", name="aux")
    u_v2.item("DEMO-RLY-2CO-24", name="coil-a")
    result_v2 = fr.build(parts, design.draft(), releases=into)
    errors = [f for f in fr.check(result_v2) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    assert u_v2.unit_id is not None
    pins_v2 = numbering_pins.pins(result_v2.model, u_v2.unit_id)
    by_last_segment = {row.key[-1]: row.text for row in pins_v2.items}
    # Free numbering, (key, id) order: "aux" sorts before "coil-a".
    assert by_last_segment == {"aux": "K1", "coil-a": "K2"}

    target_v2 = fr.release(result_v2, into, unit=u_v2)
    assert target_v2.exists()


def test_an_authored_pin_is_never_auto_seeded_onto_a_now_untagged_item(tmp_path_factory):
    """Acceptance (FD3's own words, "FD5 seeds only the assigned ones"): `coil`'s tag `K5` in
    `1.1` is an AUTHORED pin (`authored=True` in the stored file) -- deliberately a number free
    numbering would never itself produce for a single-item group, so seeding it would be
    visibly wrong. Revision `1.2` removes the tag; the seeding must skip an authored pin, so
    `coil` is numbered FRESH (`K1`, free numbering's own answer for one unnumbered item),
    never `K5`.
    """
    parts = fr.parts("demo_parts")
    into = tmp_path_factory.mktemp("authored_guard")

    design_v1 = fransys_author.Design(parts)
    u_v1 = design_v1.scope("ag").unit("authored-guard-unit", revision=1, interface="1")
    u_v1.revision(1, date="2026-09-26", text="Revision 1", created="OJB")
    u_v1.item("DEMO-RLY-2CO-24", name="coil", tag="K5")
    result_v1 = fr.build(parts, design_v1.draft())
    errors = [f for f in fr.check(result_v1) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    fr.release(result_v1, into, unit=u_v1)

    design_v2 = fransys_author.Design(parts)
    u_v2 = design_v2.scope("ag").unit("authored-guard-unit", revision=2, interface="1")
    u_v2.revision(2, date="2026-09-26", text="Revision 2", created="OJB")
    u_v2.item("DEMO-RLY-2CO-24", name="coil")
    result_v2 = fr.build(parts, design_v2.draft(), releases=into)
    errors = [f for f in fr.check(result_v2) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    assert u_v2.unit_id is not None
    pins_v2 = numbering_pins.pins(result_v2.model, u_v2.unit_id)
    (row,) = pins_v2.items
    assert row.authored is False, "the pass assigned it, the seeding never wrote a tag"
    assert row.text == "K1", "an authored pin (K5) must never be auto-seeded onto a bare item"


def test_seeding_skips_an_item_outside_the_unit_and_one_already_tagged(tmp_path_factory):
    """Coverage: `_current_item_positions`'s own-unit-only filter, exercised by a top-level
    item that belongs to no unit at all (`item.unit != unit`), and `_seed_assigned_for_unit`'s
    SC3 guard, exercised by a current item that has since become independently tagged (`coil`
    itself, `item_record.tag is not None`) -- neither is seeded, and this build still succeeds.
    """
    parts = fr.parts("demo_parts")
    into = tmp_path_factory.mktemp("seeding_skips")

    design_v1 = fransys_author.Design(parts)
    u_v1 = design_v1.scope("sk1").unit("seeding-skip-unit", revision=1, interface="1")
    u_v1.revision(1, date="2026-09-26", text="Revision 1", created="OJB")
    u_v1.item("DEMO-RLY-2CO-24", name="coil")
    result_v1 = fr.build(parts, design_v1.draft())
    errors = [f for f in fr.check(result_v1) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    fr.release(result_v1, into, unit=u_v1)

    design_v2 = fransys_author.Design(parts)
    design_v2.item("DEMO-CONN-2P", tag="P1")  # unit=None: outside every unit, line 310's OR
    u_v2 = design_v2.scope("sk1").unit("seeding-skip-unit", revision=2, interface="1")
    u_v2.revision(2, date="2026-09-26", text="Revision 2", created="OJB")
    u_v2.item("DEMO-RLY-2CO-24", name="coil", tag="K9")  # now independently tagged
    result_v2 = fr.build(parts, design_v2.draft(), releases=into)
    errors = [f for f in fr.check(result_v2) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    assert u_v2.unit_id is not None
    pins_v2 = numbering_pins.pins(result_v2.model, u_v2.unit_id)
    (row,) = pins_v2.items
    assert row.authored is True
    assert row.text == "K9"


def test_pin_source_skips_a_same_version_sibling_ordered_above_the_current_one(
    tmp_path_factory,
):
    """Coverage (`_pin_source`'s own "at or below" filter): with `1.1` and `1.3` released,
    `1.2`'s pin source is `1.1`, never `1.3` -- `1.3` sorts ABOVE `1.2` and must be skipped, not
    merely deprioritised.
    """
    parts = fr.parts("demo_parts")
    into = tmp_path_factory.mktemp("pin_source_order_skip")

    result_1, u_1 = _relay_board(parts, revision=1, coil_b=True, aux=False)
    errors = [f for f in fr.check(result_1) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    fr.release(result_1, into, unit=u_1)

    design_3 = fransys_author.Design(parts)
    u_3 = design_3.scope("rb").unit("relay-board", revision=3, interface="1")
    u_3.revision(3, date="2026-09-26", text="Revision 3", created="OJB")
    u_3.item("DEMO-RLY-2CO-24", name="coil-a")
    result_3 = fr.build(parts, design_3.draft())
    errors = [f for f in fr.check(result_3) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    fr.release(result_3, into, unit=u_3)

    result_2, u_2 = _relay_board(parts, revision=2, coil_b=False, aux=True, releases=into)
    errors = [f for f in fr.check(result_2) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    assert u_2.unit_id is not None
    pins_2 = numbering_pins.pins(result_2.model, u_2.unit_id)
    by_last_segment = {row.key[-1]: row.text for row in pins_2.items}
    assert by_last_segment["coil-a"] == "K1", "1.1's pin, not 1.3's, must be the source"
    assert by_last_segment["aux"] == "K3", "1.1's coil-b (K2) is still reserved"


def test_pin_source_skips_a_sibling_with_no_stored_numbering_file(tmp_path_factory):
    """Coverage (`_pin_source`): a same-version, in-order sibling whose own `baseline/
    numbering.json` is missing (an old release, from before this feature) is skipped, not
    read as a pin source -- the build then numbers freely, with no crash.
    """
    parts = fr.parts("demo_parts")
    into = tmp_path_factory.mktemp("pin_source_no_numbering_file")

    result_1, u_1 = _relay_board(parts, revision=1, coil_b=True, aux=False)
    errors = [f for f in fr.check(result_1) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    target_1 = fr.release(result_1, into, unit=u_1)
    (target_1 / "baseline" / "numbering.json").unlink()

    result_2, u_2 = _relay_board(parts, revision=2, coil_b=False, aux=True, releases=into)
    errors = [f for f in fr.check(result_2) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    assert u_2.unit_id is not None
    pins_2 = numbering_pins.pins(result_2.model, u_2.unit_id)
    by_last_segment = {row.key[-1]: row.text for row in pins_2.items}
    # Free numbering, (key, id) order: no pin source at all, exactly as if releases= were None.
    assert by_last_segment == {"aux": "K1", "coil-a": "K2"}


# -- MODEL-DIFF: fr.diff and release()'s changes.md/.csv (M3, M4) ---------------------------


def _second_board_release(parts, into, *, revision, version=1, wire_colour):
    """A fresh standalone build of `baseline-board` at `(version, revision)`, wire recoloured,
    released into `into` (already holding the shared fixture's first release) -- mirrors
    `_build_interface_board`'s own pattern of a complete fresh build per release, never an
    incremental edit of an already-built model.
    """
    design = fransys_author.Design(parts)
    _x1, u = _board_unit(
        design.scope("brd"), wire_colour=wire_colour, revision=revision, version=version
    )
    result = fr.build(parts, design.draft())
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    target = fr.release(result, into, unit=u)
    return result, u, target


@pytest.fixture(scope="module")
def second_board_scenario(released, tmp_path_factory):
    """The shared fixture's board, re-released once more at `1.2` (wire recoloured BU to RD),
    into its own copy of `into` -- `changes.md`/`.csv` there, plus the diff independently
    computed from the two stored listings, shared by every M3/M4 test below that needs a
    second release already in place.
    """
    _result, base_into, _board_target, _cabinet_target, _board_scope, _cabinet_scope = released
    parts = fr.parts("demo_parts")
    into = _copy_into(tmp_path_factory, base_into)
    _second_result, second_unit, second_target = _second_board_release(
        parts, into, revision=2, wire_colour="RD"
    )
    first_listing = baseline.loads(
        (into / "baseline-board" / "1.1" / "baseline" / "listing.json").read_text(encoding="utf-8")
    )
    second_listing = baseline.loads(
        (second_target / "baseline" / "listing.json").read_text(encoding="utf-8")
    )
    expected_diff = baseline.diff(first_listing, second_listing)
    expected_md = changes_markdown(expected_diff)
    expected_csv = changes_csv(expected_diff)
    return parts, into, second_target, second_unit, expected_diff, expected_md, expected_csv


def test_the_first_release_writes_neither_changes_file(released):
    """Acceptance 1: `release`'s M4 code never runs at all on a unit's first release (no
    sibling folder yet, `_previous_release_listing` returns `None`).
    """
    _result, _into, board_target, _cabinet_target, _board_scope, _cabinet_scope = released
    assert not (board_target / "changes.md").exists()
    assert not (board_target / "changes.csv").exists()


def test_a_second_release_writes_both_change_files_matching_the_independent_diff(
    second_board_scenario,
):
    """Acceptance 2: `release`'s own `changes.md`/`.csv` are byte-equal to the same diff
    computed independently from the two stored listings, and the Markdown names the actual
    wire colour change -- a content check beyond self-consistency, catching an argument-order
    regression even if this test's own diff call happened to share a bug with `release()`'s.
    """
    _parts, _into, second_target, _unit, expected_diff, expected_md, expected_csv = (
        second_board_scenario
    )
    assert expected_diff.changes, "the wire colour change must produce at least one row"
    assert (second_target / "changes.md").read_text(encoding="utf-8") == expected_md
    assert (second_target / "changes.csv").read_text(encoding="utf-8") == expected_csv
    assert "colour BU to RD" in expected_md


def test_the_manifest_lists_both_change_files_with_hashes(second_board_scenario):
    """Acceptance 3: `_manifest`'s `files` entries cover `changes.md`/`.csv` too, each with a
    `sha256` matching the actual bytes on disk.
    """
    _parts, _into, second_target, _unit, _diff, _md, _csv = second_board_scenario
    manifest = json.loads(
        (second_target / "baseline" / "manifest.json").read_text(encoding="utf-8")
    )
    files_by_path = {entry["path"]: entry for entry in manifest["files"]}
    assert {"changes.md", "changes.csv"} <= set(files_by_path)
    for name in ("changes.md", "changes.csv"):
        actual_bytes = (second_target / name).read_bytes()
        assert files_by_path[name]["sha256"] == hashlib.sha256(actual_bytes).hexdigest()


def test_sk_diff_before_releasing_matches_the_eventual_changes_md(
    released, second_board_scenario, tmp_path_factory
):
    """Acceptance 4: `fr.diff`, called on the same second-revision build BEFORE it is ever
    released, against a fresh `into` holding only the first release, gives the same Markdown
    the eventual `release()` call writes to `changes.md`.
    """
    _result, base_into, _board_target, _cabinet_target, _board_scope, _cabinet_scope = released
    _parts, _into, _second_target, _unit, _diff, expected_md, _csv = second_board_scenario
    parts = fr.parts("demo_parts")
    fresh_into = _copy_into(tmp_path_factory, base_into)
    design = fransys_author.Design(parts)
    _x1, u = _board_unit(design.scope("brd"), wire_colour="RD", revision=2)
    result = fr.build(parts, design.draft())
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors

    text = fr.diff(result, fresh_into, unit=u)
    assert text == expected_md


def test_sk_diff_with_no_release_at_all_raises_file_not_found(tmp_path_factory):
    """Acceptance 5: no `<baselines>/<name>/` directory exists at all -- `fr.diff` raises
    `FileNotFoundError`, naming the directory it looked under.
    """
    parts = fr.parts("demo_parts")
    into = tmp_path_factory.mktemp("diff_no_release")
    design = fransys_author.Design(parts)
    _x1, u = _board_unit(design.scope("brd"))
    result = fr.build(parts, design.draft())
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors

    with pytest.raises(FileNotFoundError) as exc:
        fr.diff(result, into, unit=u)
    assert "baseline-board" in str(exc.value)


def test_sk_diff_against_the_current_release_shows_only_the_unreleased_edit(
    second_board_scenario,
):
    """Acceptance 6: with `1.2` already released (wire BU to RD, `second_board_scenario`), one
    more in-memory edit at the SAME revision (wire RD to BK) makes `fr.diff`'s default branch
    read the CURRENT release folder as `a` -- the returned Markdown shows only the new edit,
    never the original `1.1` to `1.2` change.
    """
    parts, into, _second_target, _unit, _diff, _md, _csv = second_board_scenario
    design = fransys_author.Design(parts)
    _x1, u = _board_unit(design.scope("brd"), wire_colour="BK", revision=2)
    result = fr.build(parts, design.draft())
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors

    text = fr.diff(result, into, unit=u)
    assert "colour RD to BK" in text
    assert "colour BU to RD" not in text


def test_sk_diff_against_an_explicit_revision_reads_that_release_directly(
    second_board_scenario,
):
    """M3: `against=` names a specific released `<version>.<revision>` folder, read directly
    (`_stored_listing_text(candidate)`), distinct from the default branch's current-release
    lookup -- the gap MODEL-DIFF-FIX1 left open in `fransys`'s own coverage. With `1.1` (wire
    BU) and `1.2` (wire RD) both released (`second_board_scenario`) and a third, unreleased
    revision in memory (wire BK), the default call diffs against `1.2` while `against="1.1"`
    diffs against `1.1` directly -- two different bases, two different Markdown bodies, proving
    `against` was actually read rather than ignored.
    """
    parts, into, _second_target, _unit, _diff, _md, _csv = second_board_scenario
    design = fransys_author.Design(parts)
    _x1, u = _board_unit(design.scope("brd"), wire_colour="BK", revision=3)
    result = fr.build(parts, design.draft())
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors

    default_text = fr.diff(result, into, unit=u)
    against_text = fr.diff(result, into, unit=u, against="1.1")

    assert "colour RD to BK" in default_text
    assert "colour BU to RD" not in default_text

    assert "colour BU to BK" in against_text
    assert "colour RD to BK" not in against_text


def test_a_cross_version_release_gives_a_version_change_row(second_board_scenario):
    """Acceptance 7: releasing `2.1` right after `1.2` (same boundary and interface, only the
    release numbers differ) gives a `Change` row naming `version`, and `changes.md` matches
    the independently computed diff from `1.2`.
    """
    parts, into, _second_target, _unit, _diff, _md, _csv = second_board_scenario
    design = fransys_author.Design(parts)
    _x1, u = _board_unit(design.scope("brd"), wire_colour="RD", version=2, revision=1)
    result = fr.build(parts, design.draft())
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    third_target = fr.release(result, into, unit=u)

    second_listing = baseline.loads(
        (into / "baseline-board" / "1.2" / "baseline" / "listing.json").read_text(encoding="utf-8")
    )
    third_listing = baseline.loads(
        (third_target / "baseline" / "listing.json").read_text(encoding="utf-8")
    )
    expected_diff = baseline.diff(second_listing, third_listing)
    version_changes = [
        c for c in expected_diff.changes if c.section == "unit" and c.field == "version"
    ]
    assert version_changes, "a version bump must produce a version change row"

    md = (third_target / "changes.md").read_text(encoding="utf-8")
    assert "changes from 1.2 to 2.1" in md
    assert md == changes_markdown(expected_diff)


def test_a_noop_rerelease_leaves_the_change_files_mtimes_unchanged(second_board_scenario):
    """Acceptance 8: releasing the exact same model again over an already-released revision
    takes `release`'s early-return no-op path, which never reaches the M4 code at all -- both
    `changes.md` and `.csv` keep their original mtimes.
    """
    parts, into, second_target, _unit, _diff, _md, _csv = second_board_scenario
    md_mtime = (second_target / "changes.md").stat().st_mtime_ns
    csv_mtime = (second_target / "changes.csv").stat().st_mtime_ns

    design = fransys_author.Design(parts)
    _x1, u = _board_unit(design.scope("brd"), wire_colour="RD", revision=2)
    result = fr.build(parts, design.draft())
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    returned = fr.release(result, into, unit=u)
    assert returned == second_target

    assert (second_target / "changes.md").stat().st_mtime_ns == md_mtime
    assert (second_target / "changes.csv").stat().st_mtime_ns == csv_mtime


# -- L5: fr.verify (baseline spec L5, decision 0051) -----------------------------------------
# `released` and `colour_twin`, above, are step 3's own module-scope fixtures (root CLAUDE.md's
# speed rule: a test over 1 s shares its build), reused here rather than building a third pair.


def test_verify_after_the_fixtures_own_releases_is_empty(released):
    """Acceptance (baseline spec L5): with the board and cabinet both released and nothing
    changed since, `verify` reports nothing at all.
    """
    result, into, _board_target, _cabinet_target, _board_scope, _cabinet_scope = released
    assert fr.verify(result, into) == ()


def test_verify_after_the_colour_change_gives_one_baseline_differs_for_the_board(colour_twin):
    """Acceptance: `colour_twin`'s own perturbed build was never re-released -- `verify` alone,
    with no call to `release` at all, still catches the board's own drift: one
    `BASELINE_DIFFERS`, naming the board, never the cabinet (whose own listing only names the
    board by name/version/revision, untouched by its internal wiring -- the same reason
    `test_board_wire_colour_change_makes_the_cabinets_baseline_differ` names the board too when
    releasing the cabinet triggers the subtree check).
    """
    result, into, board_scope, _cabinet_scope = colour_twin
    findings = fr.verify(result, into)
    assert [f.code for f in findings] == ["BASELINE_DIFFERS"]
    (finding,) = findings
    assert finding.subjects == (board_scope.unit_id,)
    assert "conductors" in finding.message


def test_verify_gives_one_baseline_differs_per_board_instance_not_per_release(
    tmp_path_factory,
):
    """Acceptance (spec step 4's own words, "one `BASELINE_DIFFERS` per board instance"): two
    cabinets, each nesting its own instance of the SAME `baseline-board` release (equal
    content, so they dedupe onto one `UnitRelease`, `_cabinet_unit`'s own two-call pattern), one
    release each (releasing through either instance covers the shared release identity). Both
    board instances are then rebuilt with the same colour change -- `verify` must give exactly
    TWO `BASELINE_DIFFERS`, one per board INSTANCE (naming each board's own unit id), not one
    per distinct release: a `verify` that deduplicated by target path (or by release identity)
    would give only one and pass every other test in this file undetected.
    """
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    cab1_scope, board1_scope = _cabinet_unit(design.scope("cab1"), name="C1")
    _cab2_scope, _board2_scope = _cabinet_unit(design.scope("cab2"), name="C2")
    result = fr.build(parts, design.draft())
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors

    into = tmp_path_factory.mktemp("two_board_instances")
    fr.release(result, into, unit=board1_scope)
    fr.release(result, into, unit=cab1_scope)

    changed_design = fransys_author.Design(parts)
    _changed_cab1_scope, changed_board1_scope = _cabinet_unit(
        changed_design.scope("cab1"), name="C1", wire_colour="BK"
    )
    _changed_cab2_scope, changed_board2_scope = _cabinet_unit(
        changed_design.scope("cab2"), name="C2", wire_colour="BK"
    )
    changed_result = fr.build(parts, changed_design.draft())
    changed_errors = [f for f in fr.check(changed_result) if f.severity is fr.Severity.ERROR]
    assert changed_errors == [], changed_errors

    findings = fr.verify(changed_result, into)
    assert [f.code for f in findings] == ["BASELINE_DIFFERS", "BASELINE_DIFFERS"]
    subjects = {finding.subjects for finding in findings}
    assert subjects == {
        (changed_board1_scope.unit_id,),
        (changed_board2_scope.unit_id,),
    }
    assert changed_board1_scope.unit_id != changed_board2_scope.unit_id


def test_verify_gives_nothing_for_a_unit_with_no_stored_baseline(tmp_path_factory):
    """Acceptance: a unit never released at all -- `verify` against an empty baselines root
    reports nothing, the same "no stored baseline, not reported" rule L4's own nested check
    follows (`_nested_release_findings`'s `RELEASE_NESTED_UNRELEASED` branch, which `verify`
    itself never raises: it only ever answers "does it differ", never "was it released").
    """
    parts = fr.parts("demo_parts")
    result, _scope = _build_interface_board(parts, revision=1, interface="1", with_spare=False)
    errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors
    empty_into = tmp_path_factory.mktemp("verify_no_baseline")
    assert fr.verify(result, empty_into) == ()


def test_verify_writes_nothing_the_baselines_trees_hashes_and_mtimes_stay_equal(colour_twin):
    """L5: `verify` reads `<baselines>` only, never writes into it -- every file's hash and
    mtime under `into` stays exactly as `released` (this fixture's own base) left it, before and
    after a `verify` call that itself reports a real `BASELINE_DIFFERS` (not a vacuous check
    where nothing was ever read).
    """
    result, into, _board_scope, _cabinet_scope = colour_twin
    before = {
        path: (path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())
        for path in into.rglob("*")
        if path.is_file()
    }
    assert before, "the fixture's own releases wrote at least one file"

    findings = fr.verify(result, into)
    assert findings, "this test's own point is a real BASELINE_DIFFERS, not a vacuous check"

    after = {
        path: (path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())
        for path in into.rglob("*")
        if path.is_file()
    }
    assert before == after


def test_verify_checks_the_system_too_when_the_model_has_a_project(tmp_path_factory):
    """Acceptance: `verify` walks the system (`unit=None`) as well as every real unit, but
    only when the model actually holds a `Project` record (`_system_result`, above, is the one
    fixture in this file that calls `design.project(...)` at all) -- a clean system release
    verifies empty, and a second, unreleased build with one extra item gives one
    `BASELINE_DIFFERS` with `subjects == ()` (the system's own convention, `_l4_findings`'s own
    words for `REVISION_ALREADY_RELEASED`, shared here since there is no unit id to name).
    """
    into = tmp_path_factory.mktemp("verify_system")
    first = _system_result(extra_item=False)
    fr.release(first, into)
    assert fr.verify(first, into) == ()

    second = _system_result(extra_item=True)
    findings = fr.verify(second, into)
    assert [f.code for f in findings] == ["BASELINE_DIFFERS"]
    (finding,) = findings
    assert finding.subjects == ()


def test_verify_skips_the_system_with_no_project_record_at_all(released):
    """Acceptance: `released`'s own fixture build authors no `Project` at all (`_cabinet_unit`/
    `_board_unit` never call `design.project(...)`), so `baseline.listing(model, None)` -- and
    `_release_target(model, None, ...)`'s own `project.number` -- has nothing to read; `verify`
    must skip the system entirely rather than raise, which is exactly why this fixture's own
    `test_verify_after_the_fixtures_own_releases_is_empty` above passes at all instead of
    crashing on an empty `projects(model)`.
    """
    result, into, _board_target, _cabinet_target, _board_scope, _cabinet_scope = released

    assert not projects(result.model), "this fixture's own point: no Project record exists"
    assert fr.verify(result, into) == ()
