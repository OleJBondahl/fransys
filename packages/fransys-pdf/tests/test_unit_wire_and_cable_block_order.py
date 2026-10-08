"""A unit document lists its cable blocks first (CD12), then wire-only harness blocks (pdf-0024)."""

from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import BU
from fransys_pdf._drawings import cable_blocks, harness_cables_for

from fransys_model.derive.cable_drawing import cable_block_key
from fransys_model.vocab import DocumentPreset, PageKind, documents, items


class _Open(NamedTuple):
    """The unit exposes nothing."""


@fr.unit("demo-mixed", revision=1, interface_version=1, date="2026-10-08", text="First", by="XX")
def _mixed(u: fr.Design) -> _Open:
    u.location("C1", "Cabinet")
    loom = u.harness("A1", place="C1")
    near = u.device("P1", "DEMO-CONN-2P", parent=loom, place="C1")
    far = u.device("P2", "DEMO-CONN-2P", parent=loom, place="C1")
    u.wire(near[1], far[1], wire=(BU, 0.5))
    a = u.device("Q1", "DEMO-CONN-2P", place="C1")
    b = u.device("Q2", "DEMO-CONN-2P", place="C1")
    u.cable("Z9", "DEMO-CBL-4G1.5", place="C1").core(1, a[1], b[1])
    return _Open()


def test_the_cable_block_comes_before_the_wire_only_block(tmp_path: Any) -> None:
    """Sorting by key, or putting wires first, would put the harness `A1` before cable `Z9`."""
    cover = tmp_path / "cover.md"
    cover.write_text("# Mixed\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_mixed, "U1", place=None)
    model = fr.build(
        d, fr.document(DocumentPreset.HARNESS_DRAWING, "demo-mixed", cover=cover)
    ).model
    ((_, record),) = documents(model).items()
    pages = (PageKind.HARNESS_DRAWING,)
    blocks = cable_blocks(model, record, harness_cables_for(model, record, pages))
    by_key = {it.key[-1]: i for i, it in items(model).items()}
    unit = next(u for u in {it.unit for it in items(model).values()} if u is not None)
    expected = [cable_block_key(unit, by_key["Z9"]), cable_block_key(unit, by_key["A1"])]
    assert [b.key for b in blocks] == expected


@fr.unit("demo-wires", revision=1, interface_version=1, date="2026-10-08", text="First", by="XX")
def _wires(u: fr.Design) -> _Open:
    u.location("C1", "Cabinet")
    for tag in ("W10", "W2", "W1"):
        loom = u.harness(tag, place="C1")
        near = u.device(f"{tag}A", "DEMO-CONN-2P", parent=loom, place="C1")
        far = u.device(f"{tag}B", "DEMO-CONN-2P", parent=loom, place="C1")
        u.wire(near[1], far[1], wire=(BU, 0.5))
    return _Open()


def test_wire_only_blocks_print_in_natural_designation_order(tmp_path: Any) -> None:
    """Catches an Id sort of the wire-only harnesses: it prints W1, W10, W2."""
    cover = tmp_path / "cover.md"
    cover.write_text("# Wires\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_wires, "U1", place=None)
    model = fr.build(
        d, fr.document(DocumentPreset.HARNESS_DRAWING, "demo-wires", cover=cover)
    ).model
    ((_, record),) = documents(model).items()
    pages = (PageKind.HARNESS_DRAWING,)
    blocks = cable_blocks(model, record, harness_cables_for(model, record, pages))
    by_key = {it.key[-1]: i for i, it in items(model).items()}
    unit = next(u for u in {it.unit for it in items(model).values()} if u is not None)
    expected = [cable_block_key(unit, by_key[tag]) for tag in ("W1", "W2", "W10")]
    assert [b.key for b in blocks] == expected
