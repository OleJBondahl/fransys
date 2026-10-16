"""`StoredReleases`: the facade fills it from release folders; derive picks from it (model-0267).

One module fixture releases the board twice (1.1, 1.2) into one folder; the tests read it.
"""

import sys
from pathlib import Path

import fransys as fr
import fransys_author
import pytest
from fransys._release_reader import read_stored

from fransys_model.derive import (
    manifest_rows,
    nested_units,
    pin_source,
    previous_release,
    release_identity,
)
from fransys_model.vocab import units_named

sys.path.insert(0, str(Path(__file__).parent))
from release_folders_fixture import build_board, release_board

_HISTORY = [(1, 1, "2026-09-26"), (1, 2, "2026-09-27")]


def _folder(release):
    return None if release is None else release.folder


@pytest.fixture(scope="module")
def into(tmp_path_factory):
    root = tmp_path_factory.mktemp("stored")
    release_board(root, revision=1, history=_HISTORY[:1])
    release_board(root, revision=2, history=_HISTORY)
    return root


@pytest.fixture(scope="module")
def board():
    """`(model, unit id)` of the board as it stands at revision 1.2."""
    result, _scope = build_board(revision=2, history=_HISTORY)
    return result.model, units_named(result.model, "wb-board")[0]


def test_read_stored_fills_every_folder_with_a_listing(into):
    stored = read_stored(into / "wb-board")
    assert [r.folder for r in stored.releases] == ["1.1", "1.2"]
    first = stored.releases[0]
    assert (first.identity.name, first.order) == ("wb-board", (1, 1))
    assert first.numbering is not None


def test_a_missing_name_folder_gives_no_releases(tmp_path):
    assert read_stored(tmp_path / "nothing").releases == ()


def test_previous_and_pin_source_over_the_read_folders(into, board):
    model, unit = board
    stored, identity = read_stored(into / "wb-board"), release_identity(model, unit)
    assert _folder(previous_release(stored, identity)) == "1.1"
    assert _folder(pin_source(stored, identity)) == "1.2"


def test_manifest_rows_of_the_board(board):
    model, unit = board
    rows = manifest_rows(model, unit)
    assert (rows.identity.name, rows.identity.revision, rows.nested) == ("wb-board", 2, ())
    assert rows.entry is not None
    assert rows.entry.text == "Revision 1.2"
    assert [(r.name, r.version) for r in rows.part_libraries] == [("demo-parts", "0.1.0")]


def test_two_instances_of_one_release_give_one_nested_row():
    """Two units of one release hash to one listing digest, so the system has one nested row."""
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    design.project(title="WB system", number="P-WB", customer="Demo", revision=1, author="OJB")
    design.revision(1, version=1, date="2026-09-26", text="Revision 1", created="OJB")
    for tag in ("a", "b"):
        u = design.scope(tag).unit("wb-board", version=1, revision=1, interface="1")
        u.revision(1, date="2026-09-26", text="Revision 1", created="OJB")
        u.boundary(u.item("DEMO-CONN-2P", tag="X1", group=u.group("BRD", "I/O board")))
    model = fr.build(parts, design.draft()).model
    assert len(nested_units(model, None)) == 2
    assert [(r.name, len(r.listing_digest)) for r in manifest_rows(model, None).nested] == [
        ("wb-board", 64)
    ]
