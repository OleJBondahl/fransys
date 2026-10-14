"""Field case: an external device is a dashed box on the block diagram, system and unit alike.

The engineering shape: seven connector devices joined by six cables, two of them supplied by
others (`external=True`). Read at the top of the system, and read inside a unit holding all seven.

Reported as a bug: the block diagram of a unit drew no dashed box for the two external devices.
It was a bug: external-items spec Y3 left a unit's own drawing set unmarked; OUTLINES BO4
(2026-10-14) removed that. Both readings dash each external device (block-diagrams spec BD4).
"""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest

from fransys_model.layout import DiagramBox, layout_of

_EDGES = (("P7", "P2"), ("P1", "P7"), ("P5", "P1"), ("P3", "P1"), ("P4", "P1"), ("P6", "P1"))
_TAGS = ("P1", "P2", "P3", "P4", "P5", "P6", "P7")
_EXTERNAL = ("P3", "P6")


class _Open(NamedTuple):
    pass


def _wire(d: Any) -> None:
    devices = {tag: d.device(tag, "DEMO-CONN-2P", external=tag in _EXTERNAL) for tag in _TAGS}
    for n, (a, b) in enumerate(_EDGES, start=1):
        d.cable(f"W{n}", "DEMO-CBL-4G1.5", length_m=2).core(1, devices[a][1], devices[b][1])


@fr.unit("by-others", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _unit(u: Any) -> _Open:
    _wire(u)
    return _Open()


@cache
def _built(*, in_unit: bool) -> fr.BuildResult:
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# By others\n", encoding="utf-8")
        d = fr.design("demo_parts")
        if in_unit:
            d.add(_unit, "U1")
            doc = fr.document(
                fr.DocumentPreset.CABINET_SCHEMATIC,
                "by-others",
                cover=cover,
                add=(fr.PageKind.BLOCK_DIAGRAM,),
            )
        else:
            _wire(d)
            doc = fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover)
        return fr.build(d, doc)


@pytest.mark.parametrize(
    ("in_unit", "dashed"), [(False, len(_EXTERNAL)), (True, len(_EXTERNAL))], ids=["system", "unit"]
)
def test_every_reading_dashes_each_external_device(*, in_unit: bool, dashed: int) -> None:
    boxes = layout_of(_built(in_unit=in_unit).model, DiagramBox).values()
    assert len(boxes) == len(_TAGS)
    assert sum(box.dashed for box in boxes) == dashed
