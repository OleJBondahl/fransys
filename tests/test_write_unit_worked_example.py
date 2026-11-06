"""`fr.write(result, out_dir, unit=)` and `fr.document(...)`'s new subject
kinds, proven against the units worked example's real, facade-built geometry (STEP 5).

Does not modify `test_units_worked_example.py`'s shared fixture functions
"""
# CONNECTION_NOT_DRAWN 4 per default-salt build set (MATES-DISABLED): mated, harness or board-unit input, refused for 0.22 (R1216).

import re
import tempfile
from pathlib import Path

import fransys as fr
import fransys_parts
import pytest
from _model_build_cover import system_document
from fransys_author.design import Design
from test_units_worked_example import _system_design

from fransys_model.derive import unit_name_unresolved, unit_release
from fransys_model.kernel import Id, SchemaError
from fransys_model.vocab import Document as ModelDocument
from fransys_model.vocab.tables import units as units_table


def _only_record(draft) -> ModelDocument:
    (record,) = draft.records()
    assert isinstance(record, ModelDocument)
    return record


# The pump1 unit=write's exact expected file set (the table of this fixture's real
# strips/boards/racks): its own cabinet document, the five whole-model-shaped CSVs (each
# correctly scoped to pump1 alone, cables.csv included), and pump1's own strip's terminal list.
# No overview.html (a system view), no connectors-* (the board's connector belongs to the
# nested board unit, not the cabinet), no board.pdf or system.pdf (neither document names
# pump1 as its subject).
_PUMP1_WRITE_FILES = frozenset(
    {
        "demo-pump-cabinet-v1.2-bom.csv",
        "demo-pump-cabinet-v1.2-cables.csv",
        "demo-pump-cabinet-v1.2-cores.csv",
        "demo-pump-cabinet-v1.2.pdf",
        "demo-pump-cabinet-v1.2-designations.csv",
        "demo-pump-cabinet-v1.2-plc.csv",
        "demo-pump-cabinet-v1.2-terminals.csv",
        "demo-pump-cabinet-v1.2-wires.csv",
    }
)

# The pump1 io-board unit's own write (the table): its own CABINET_SCHEMATIC
# document, the five whole-model-shaped CSVs (scoped to the board alone), and the board
# item's own connector list (`_subjects.boards`'s predicate -- a PLC-module parent -- the
# board unit's `x1` connector, not a strip: no terminals-* file). No overview.html (a system
# view), no cabinet.pdf or system.pdf (neither document names the board as its subject).
# Confirmed by running `fr.write(result, tmp_path, unit=pump1_board)`, not guessed.
_PUMP1_BOARD_WRITE_FILES = frozenset(
    {
        "demo-io-board-v1.3.pdf",
        "demo-io-board-v1.3-bom.csv",
        "demo-io-board-v1.3-cables.csv",
        "demo-io-board-v1.3-cores.csv",
        "demo-io-board-v1.3-connectors.csv",
        "demo-io-board-v1.3-designations.csv",
        "demo-io-board-v1.3-plc.csv",
        "demo-io-board-v1.3-wires.csv",
    }
)

# The whole model's own write (`unit=None`): every document (cabinet, board, system), every
# whole-model CSV including `cables.csv` (root decision 0016, STEP 6) and `overview.html`,
# and the one terminal list and the one connector list of the whole model with no unit filter --
# both pump1's and pump2's strips, both io-boards' connectors. Confirmed by running
# `fr.write(result, tmp_path / "all", unit=None)`, not guessed.
_ALL_WRITE_FILES = frozenset(
    {
        "demo-io-board-v1.3-P1-U1.pdf",
        "demo-io-board-v1.3-P2-U1.pdf",
        "demo-pump-cabinet-v1.2-P1.pdf",
        "demo-pump-cabinet-v1.2-P2.pdf",
        "P-1001-v1.1-bom.csv",
        "P-1001-v1.1-cables.csv",
        "P-1001-v1.1-cores.csv",
        "P-1001-v1.1-connectors.csv",
        "P-1001-v1.1-designations.csv",
        "P-1001-v1.1-overview.html",
        "P-1001-v1.1-plc.csv",
        "P-1001-v1.1.pdf",
        "P-1001-v1.1-terminals.csv",
        "P-1001-v1.1-wires.csv",
    }
)


def _unit_id(model, *, name, prefix):
    """The one unit of `model` named `name` whose own key starts with `prefix`."""
    all_units = units_table(model)
    return next(unit_id for unit_id, unit in all_units.items() if unit_release(model, unit_id).name == name and unit.key[0] == prefix)


def _cover(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def _covers():
    covers = Path(tempfile.mkdtemp())
    return {
        "cabinet": _cover(covers, "cabinet.md", "# Cabinet\n"),
        "board": _cover(covers, "board.md", "# Board\n"),
        "system": _cover(covers, "system.md", "# System\n"),
    }


@pytest.fixture(scope="module")
def built(_covers):
    """The units worked example, built with its own real `fr.document(...)` records:
    pump1's cabinet document (subject its unit id), pump1's board document (subject its
    nested unit's id) and the system document (subject `None`) -- so "no board document in
    out/cabinet" and "no system.pdf in out/cabinet" are non-vacuous: both documents genuinely
    """
    parts = fransys_parts.load("demo_parts")
    d, _field1, _field2 = _system_design(parts, tags=("P1", "P2"))
    draft = d.draft()
    probe_model = fr.build(parts, draft, system_document()).model
    pump1_cabinet = _unit_id(probe_model, name="demo-pump-cabinet", prefix="pump1")
    pump1_board = _unit_id(probe_model, name="demo-io-board", prefix="pump1")
    pump2_cabinet = _unit_id(probe_model, name="demo-pump-cabinet", prefix="pump2")

    cabinet_doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, pump1_cabinet, cover=_covers["cabinet"])
    board_doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, pump1_board, cover=_covers["board"])
    system_doc = fr.document(fr.DocumentPreset.SYSTEM, None, cover=_covers["system"])
    # pump2's cabinet set is printed too (UNPRINTED_SET)
    cabinet2_doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, pump2_cabinet, cover=_covers["cabinet"])

    board2_doc = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC,
        _unit_id(probe_model, name="demo-io-board", prefix="pump2"),
        cover=_covers["board"],
    )
    result = fr.build(parts, draft, cabinet_doc, cabinet2_doc, board_doc, board2_doc, system_doc)
    return result, pump1_cabinet, pump2_cabinet, pump1_board


@pytest.fixture(scope="module")
def pump1_cabinet_write(built, tmp_path_factory):
    result, pump1_cabinet, _pump2_cabinet, _pump1_board = built
    return fr.write(result, tmp_path_factory.mktemp("pump1_cabinet"), unit=pump1_cabinet)


# -- acceptance: demo_system's pump1 folder holds exactly U6's table --------------------------


def test_write_unit_pump1_writes_exactly_its_own_file_set(pump1_cabinet_write):
    written = pump1_cabinet_write
    assert {p.name for p in written} == _PUMP1_WRITE_FILES


def test_write_unit_pump1_excludes_pump2s_own_terminal_list(pump1_cabinet_write):
    """The discriminating assertion: both cabinets share the unit *name*
    `demo-pump-cabinet`, so this proves the filter matches the specific unit *instance* id,
    not the name. A unit folder's names are unit-relative (UNIT-ID I5), so both cabinets'
    strip lists are `terminals.csv`: what tells them apart is the content (pump1's field
    """
    written = pump1_cabinet_write
    (terminals,) = (p for p in written if "terminals" in p.name)
    assert terminals.name == "demo-pump-cabinet-v1.2-terminals.csv"
    text = terminals.read_text(encoding="utf-8")
    assert "+FLD-M1:U" in text
    assert "+FLD-M2:U" not in text


def test_write_unit_pump1_excludes_the_nested_boards_connector_list(pump1_cabinet_write):
    """The io-board's connector belongs to the board's own (nested) unit, not the cabinet's
    ("each nested unit is a set of its own")."""
    written = pump1_cabinet_write
    assert not any("connectors-" in p.name for p in written)
    assert "demo-io-board-v1.3.pdf" not in {p.name for p in written}


def test_write_unit_none_and_pump2_also_succeed(built, tmp_path):
    """The fixture fix (field terminals now really wired, U5): the whole-model write and
    pump2's own both succeed too, no `BuildFailedError` anywhere -- there is no more unresolved
    `BOUNDARY_UNCONNECTED` in this fixture for any of the three to trip over.
    """
    result, _pump1_cabinet, pump2_cabinet, _pump1_board = built
    written_all = fr.write(result, tmp_path / "all", unit=None)
    assert {p.name for p in written_all} == _ALL_WRITE_FILES
    written_pump2 = fr.write(result, tmp_path / "pump2", unit=pump2_cabinet)
    (terminals,) = (p for p in written_pump2 if "terminals" in p.name)
    assert terminals.name == "demo-pump-cabinet-v1.2-terminals.csv"
    text = terminals.read_text(encoding="utf-8")
    assert "+FLD-M2:U" in text
    assert "+FLD-M1:U" not in text


def test_write_unit_pump1_board_writes_exactly_its_own_file_set(built, tmp_path):
    result, _pump1_cabinet, _pump2_cabinet, pump1_board = built
    written = fr.write(result, tmp_path, unit=pump1_board)
    assert {p.name for p in written} == _PUMP1_BOARD_WRITE_FILES


# -- fr.document(...): one test per new subject kind ---------------------------


def test_document_subject_none_is_the_system_preset(tmp_path):
    cover = _cover(tmp_path, "system.md", "# System\n")
    draft = fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover)
    record = _only_record(draft)
    assert record.location is None
    assert record.item is None
    assert record.unit is None


def test_document_subject_none_with_a_non_system_preset_raises(tmp_path):
    """Confirmed empirically, not guessed: the model's own `Document.__post_init__` already
    refuses a `system`-shaped subject (none of the three) on any other preset."""
    cover = _cover(tmp_path, "cabinet.md", "# Cabinet\n")
    with pytest.raises(SchemaError):
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, None, cover=cover)


@pytest.mark.parametrize("subject", [lambda u: u, lambda u: u.unit_id], ids=["unit-scope", "raw-unit-id"])
def test_document_subject_a_unit(tmp_path, subject):
    d = Design(fr.parts())
    u = d.scope("cab").unit("demo-unit", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    cover = _cover(tmp_path, "cabinet.md", "# Cabinet\n")
    draft = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, subject(u), cover=cover)
    record = _only_record(draft)
    assert record.unit == u.unit_id
    assert record.location is None
    assert record.item is None


def test_document_subject_a_plain_scope_or_bare_design_raises_type_error(tmp_path):
    cover = _cover(tmp_path, "cabinet.md", "# Cabinet\n")
    d = Design(fr.parts())
    plain_scope = d.scope("cab")
    with pytest.raises(TypeError, match="unit"):
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, plain_scope, cover=cover)
    with pytest.raises(TypeError, match="unit"):
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, d, cover=cover)


# -- write(unit=)'s own refusal ------------------------------------------------------------


def test_write_unit_a_plain_scope_or_bare_design_raises_type_error(tmp_path):
    """A cheap hand-built model: `_resolve_unit` raises before touching the model at all."""
    d = Design(fr.parts())
    d.project(title="t", number="n", customer="c", revision=1, author="a")
    d.revision(1, date="2026-09-23", text="First issue", created="XX")
    result = fr.build(fr.parts(), d.draft(), system_document())
    plain_scope = d.scope("cab")
    with pytest.raises(TypeError, match="unit"):
        fr.write(result, tmp_path, unit=plain_scope)
    with pytest.raises(TypeError, match="unit"):
        fr.write(result, tmp_path, unit=d)


def test_write_unit_accepts_a_scope_directly(tmp_path):
    """The spec's own call shape: `unit=` takes the `Scope` `s.unit(...)` returns directly,
    not `.unit_id` narrowed out of it first (`_resolve_unit`'s `Scope` branch)."""
    d = Design(fr.parts())
    d.project(title="t", number="n", customer="c", revision=1, author="a")
    d.revision(1, date="2026-09-23", text="First issue", created="XX")
    unit_scope = d.scope("cab").unit("demo-unit", revision=1, interface="1")
    unit_scope.revision(1, date="2026-01-01", text="First release", created="XX")
    result = fr.build(fr.parts(), d.draft(), system_document())
    written = fr.write(result, tmp_path, unit=unit_scope)
    assert len(written) > 0


def test_write_unit_a_wrong_kind_id_raises_type_error(tmp_path):
    """A model `Id` of a kind other than `unit` is refused (`_resolve_unit`'s `Id` branch)."""
    d = Design(fr.parts())
    d.project(title="t", number="n", customer="c", revision=1, author="a")
    d.revision(1, date="2026-09-23", text="First issue", created="XX")
    result = fr.build(fr.parts(), d.draft(), system_document())
    wrong_kind_id = Id(kind="item", value="x")
    with pytest.raises(TypeError):
        fr.write(result, tmp_path, unit=wrong_kind_id)


# -- write(unit=)'s `str` argument, a unit release's name (UN4) ----------------------------


def test_write_unit_str_name_writes_the_same_files_as_the_scope(tmp_path):
    """`write(..., unit="name")` resolves through Part 2's `units_named` to the same unit
    `write(..., unit=<scope>)` does, when exactly one unit instance is a release of that
    name: same file-name set, and identical bytes for a shared CSV."""
    d = Design(fr.parts())
    d.project(title="t", number="n", customer="c", revision=1, author="a")
    d.revision(1, date="2026-09-23", text="First issue", created="XX")
    unit_scope = d.scope("cab").unit("relay-board", revision=1, interface="1")
    unit_scope.revision(1, date="2026-01-01", text="First release", created="XX")
    result = fr.build(fr.parts(), d.draft(), system_document())

    by_scope = fr.write(result, tmp_path / "by-scope", unit=unit_scope)
    by_name = fr.write(result, tmp_path / "by-name", unit="relay-board")

    assert {p.name for p in by_scope} == {p.name for p in by_name}
    assert (tmp_path / "by-scope" / "data" / "relay-board-v1.1-bom.csv").read_bytes() == (
        tmp_path / "by-name" / "data" / "relay-board-v1.1-bom.csv"
    ).read_bytes()


def test_write_unit_str_unknown_name_raises_value_error(tmp_path):
    """No release of that name exists: `ValueError`'s message is `unit_name_unresolved`'s
    own sentence verbatim, not a second copy of it."""
    d = Design(fr.parts())
    d.project(title="t", number="n", customer="c", revision=1, author="a")
    d.revision(1, date="2026-09-23", text="First issue", created="XX")
    result = fr.build(fr.parts(), d.draft(), system_document())
    expected = unit_name_unresolved(result.model, "no-such-unit")
    with pytest.raises(ValueError, match=re.escape(expected)) as excinfo:
        fr.write(result, tmp_path, unit="no-such-unit")
    assert str(excinfo.value) == expected


def test_write_unit_str_two_instances_of_the_same_name_raises_value_error(tmp_path):
    """Two `Unit` instances of the same release name: `units_named` finds both, so `write`
    raises the same `unit_name_unresolved` sentence (not exactly one match)."""
    d = Design(fr.parts())
    d.project(title="t", number="n", customer="c", revision=1, author="a")
    d.revision(1, date="2026-09-23", text="First issue", created="XX")
    first = d.scope("cab1").unit("dup-name", revision=1, interface="1")
    first.revision(1, date="2026-01-01", text="First release", created="XX")
    second = d.scope("cab2").unit("dup-name", revision=1, interface="1")
    second.revision(1, date="2026-01-01", text="First release", created="XX")
    result = fr.build(fr.parts(), d.draft(), system_document())
    expected = unit_name_unresolved(result.model, "dup-name")
    with pytest.raises(ValueError, match=re.escape(expected)) as excinfo:
        fr.write(result, tmp_path, unit="dup-name")
    assert str(excinfo.value) == expected
