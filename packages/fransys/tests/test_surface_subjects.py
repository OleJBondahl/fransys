"""EA15 on the facade: ids after a build, subjects by handle or release name, the exports."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.pipeline import _resolve_unit

from fransys_model.vocab import DocumentPreset


class _Board(NamedTuple):
    X1: fr.Device


@fr.unit("demo-io-board", revision=1, interface_version=1, date="2026-02-02", text="first", by="XX")
def _board(d: fr.Design) -> _Board:
    return _Board(d.device("X1", "DEMO-CONN-2P", interface=True))


def _cabinet() -> tuple[fr.Design, Any, _Board]:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    io = d.add(_board, "IO")
    p1 = d.device("P1", "DEMO-CONN-2P")
    d.mate(p1, io.X1)
    return d, p1, io


def _cover(tmp_path):
    path = tmp_path / "cabinet.md"
    path.write_text("# Demo\n", encoding="utf-8")
    return path


def test_device_and_function_ids_are_read_by_derive_after_a_build() -> None:
    d, p1, _ = _cabinet()
    model = fr.build(d).model
    assert fr.derive.items(model)[p1.id].tag == "P1"
    assert fr.derive.functions(model)[p1.x1.id].item == p1.id


def test_a_document_takes_a_device_and_a_release_name(tmp_path) -> None:
    _, p1, _ = _cabinet()
    by_device = fr.document(DocumentPreset.HARNESS_DRAWING, p1, cover=_cover(tmp_path))
    (record,) = _records(by_device)
    assert record.item == p1.id
    by_unit = fr.document(DocumentPreset.PCB_SCHEMATIC, "demo-io-board", cover=_cover(tmp_path))
    (record,) = _records(by_unit)
    assert record.unit_name == "demo-io-board"


def test_a_unit_is_named_by_its_release_name_only() -> None:
    d, _, io = _cabinet()
    model = fr.build(d).model
    by_name = _resolve_unit(model, "demo-io-board")
    assert by_name is not None
    with pytest.raises(TypeError):
        _resolve_unit(model, io)
    with pytest.raises(TypeError):
        _resolve_unit(model, 7)


def test_the_public_names_of_ea15() -> None:
    assert {"CONTROL", "SIGNAL", "GENERIC", "parts_module"} <= set(fr.__all__)
    assert "Wire" not in fr.__all__
    assert "unit_ids" not in fr.derive.__all__


def _records(document) -> list[Any]:
    """The document's records, typed loosely: the subject kinds differ."""
    return list(document.records())
