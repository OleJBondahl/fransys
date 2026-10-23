"""`fr.document` takes what `d.add` returned: one unit instance of a release added twice (R363).

Each placement writes its own PDF, named with its tag (model-0361);
the same placement twice still clashes.
"""

from typing import NamedTuple
lazy from pathlib import Path

import fransys as fr
import pytest

from fransys_model.derive import document_unit
from fransys_model.vocab.tables import documents


class _Io(NamedTuple):
    X1: fr.Device


@fr.unit("demo-io-board", revision=1, interface_version=1, date="2026-02-02", text="First", by="XX")
def _board(u: fr.Design) -> _Io:
    return _Io(u.device("X1", "DEMO-CONN-2P", interface=True))


def test_each_instance_of_one_release_gets_its_own_document(tmp_path: Path) -> None:
    cover = tmp_path / "c.md"
    cover.write_text("# Cover\n", encoding="utf-8")
    d = fr.design("demo_parts")
    first, second = d.add(_board, "U1"), d.add(_board, "U2")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    result = fr.build(d, *(fr.document(preset, one, cover=cover) for one in (first, second)))
    units = {document_unit(result.model, doc) for doc in documents(result.model)}
    assert len(units) == 2
    assert None not in units
    assert "DOCUMENT_UNIT_UNRESOLVED" not in {f.code for f in result.findings}


def test_a_result_that_d_add_did_not_return_is_refused(tmp_path: Path) -> None:
    cover = tmp_path / "c.md"
    cover.write_text("# Cover\n", encoding="utf-8")
    with pytest.raises(TypeError, match=r"what `d\.add` returned"):
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, ("not a unit",), cover=cover)


def _two_placements(tmp_path: Path, *, same: bool) -> tuple[fr.BuildResult, Path]:
    cover = tmp_path / "c.md"
    cover.write_text("# Cover\n", encoding="utf-8")
    d = fr.design("demo_parts")
    first, second = d.add(_board, "U1", unused=("X1",)), d.add(_board, "U2", unused=("X1",))
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    other = fr.DocumentPreset.PCB_SCHEMATIC
    subjects = ((preset, first), (other, first)) if same else ((preset, first), (preset, second))
    return fr.build(
        d, *(fr.document(kind, one, cover=cover) for kind, one in subjects)
    ), tmp_path / "out"


def test_two_placements_of_one_release_write_pdfs_named_by_their_tags(tmp_path: Path) -> None:
    result, out = _two_placements(tmp_path, same=False)
    names = {p.name for p in fr.write(result, out) if p.suffix == ".pdf"}
    assert names == {"demo-io-board-v1.1-U1.pdf", "demo-io-board-v1.1-U2.pdf"}


def test_one_placement_in_two_presets_still_clashes_on_its_pdf_name(tmp_path: Path) -> None:
    result, out = _two_placements(tmp_path, same=True)
    with pytest.raises(Exception, match="EXPORT_NAME_CLASH"):
        fr.write(result, out)
