"""A harness with single wires and no cable draws one block of its own (HA-H1 A1, HA-D6).

Before, a HARNESS_DRAWING document on such a harness stopped with "the harness has no cable".
"""

from typing import Any

import fransys as fr
from fransys.colours import BU
from fransys_pdf import check, source

from fransys_model.derive.cable_drawing import cable_block_key
from fransys_model.vocab import DocumentPreset, documents, items

_PLUG = "DEMO-CONN-2P"
_NO_DRAWINGS = "DOCUMENT_NO_DRAWINGS"


def _built(tmp_path: Any, tag: str, *, wires: bool, loose: bool = False) -> tuple[Any, Any]:
    """A model with harness `tag` (plugs, wired or not), its HARNESS_DRAWING document id."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    with d.function(tag, f"Loom {tag}"):
        loom = d.harness(tag, place="L0")
        near = d.device("J1", _PLUG, parent=loom, place="L0")
        far = d.device("J2", _PLUG, parent=loom, place="L0")
        if wires:
            d.wire(near[1], far[1], wire=(BU, 0.5))
    if loose:
        with d.function("X", "Loose"):
            a = d.device("A1", _PLUG, place="L0")
            b = d.device("A2", _PLUG, place="L0")
        d.wire(a[1], b[1], wire=(BU, 0.5))
    cover = tmp_path / "cover.md"
    cover.write_text("# Cover\n", encoding="utf-8")
    probe = fr.build(d).model
    (harness,) = [i for i, it in items(probe).items() if "/".join(it.key) == f"{tag}/{tag}"]
    doc = fr.document(DocumentPreset.HARNESS_DRAWING, harness, cover=cover)
    model = fr.build(d, doc).model
    (doc_id,) = [k for k, r in documents(model).items() if r.item == harness]
    return model, (harness, doc_id)


def _messages(model: Any) -> list[str]:
    return [f.message for f in check(model, {}) if f.code == _NO_DRAWINGS]


def test_a_wire_only_harness_asks_for_its_block_not_a_cable(tmp_path):
    """One 'missing drawing for <key>' finding. Restoring the has-no-cable branch changes the
    message; dropping the block makes the finding vanish or repeat."""
    model, (harness, _doc) = _built(tmp_path, "W1", wires=True)
    assert _messages(model) == [
        f"HARNESS_DRAWING: missing drawing for {cable_block_key(None, harness)}"
    ]


def test_a_wire_only_harness_with_its_svg_is_clean_and_embeds_it(tmp_path):
    """Supplying the block's svg clears the finding and `source` embeds it. Restoring the
    no-drawings page in `harness_drawing_source` would leave the svg out."""
    model, (harness, doc_id) = _built(tmp_path, "W1", wires=True)
    svgs = {cable_block_key(None, harness): "<svg>wire-only-marker</svg>"}
    assert [f for f in check(model, svgs) if f.code == _NO_DRAWINGS] == []
    assert "wire-only-marker" in source(model, doc_id, svgs)


def test_a_harness_with_neither_cable_nor_wire_still_has_no_cable(tmp_path):
    """The has-no-cable message stays for an empty harness; a block for every harness would
    break it."""
    model, _ids = _built(tmp_path, "W2", wires=False)
    assert _messages(model) == ["HARNESS_DRAWING: the harness has no cable"]


def test_a_loose_wire_gives_the_wired_harness_only_its_own_block(tmp_path):
    """A wire on no harness adds no block: exactly the harness's key is asked for. Taking every
    wire in the model would add a second key or the loose wire's."""
    model, (harness, _doc) = _built(tmp_path, "W1", wires=True, loose=True)
    assert _messages(model) == [
        f"HARNESS_DRAWING: missing drawing for {cable_block_key(None, harness)}"
    ]
