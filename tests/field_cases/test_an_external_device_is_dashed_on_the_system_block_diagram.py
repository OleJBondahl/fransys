"""Field case: seven connector devices joined by six cables, two of them supplied by others (external=True), read at system level.
The bug: a unit's block diagram drew no dashed box for its two external devices (external-items spec Y3 left its set unmarked).
Fixed by OUTLINES BO4 (2026-10-14, block-diagrams BD4), each external device is dashed on the system block diagram."""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any

import fransys as fr

from electrical_symbols import LIBRARY
from fransys_layout import lay_out_diagrams

_EDGES = (("P7", "P2"), ("P1", "P7"), ("P5", "P1"), ("P3", "P1"), ("P4", "P1"), ("P6", "P1"))
_TAGS = ("P1", "P2", "P3", "P4", "P5", "P6", "P7")
_EXTERNAL = ("P3", "P6")


def _wire(d: Any) -> None:
    devices = {tag: d.device(tag, "DEMO-CONN-2P", external=tag in _EXTERNAL) for tag in _TAGS}
    for n, (a, b) in enumerate(_EDGES, start=1):
        d.cable(f"W{n}", "DEMO-CBL-4G1.5", length_m=2).core(1, devices[a][1], devices[b][1])


@cache
def _built() -> fr.BuildResult:
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# By others\n", encoding="utf-8")
        d = fr.design("demo_parts")
        _wire(d)
        return fr.build(d, fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover))


def test_the_system_reading_dashes_each_external_device() -> None:
    diagrams, _ = lay_out_diagrams(_built().model, LIBRARY)
    boxes = tuple(box for d in diagrams.diagrams for sheet in d.sheets for box in sheet.boxes)
    assert len(boxes) == len(_TAGS)
    assert sum(box.dashed for box in boxes) == len(_EXTERNAL)
