"""Field case: a skid unit passes up its cabinet unit's terminal strip (layout-0162).

The engineering shape: a skid unit holds a cabinet unit; the skid's boundary is the cabinet's
field terminal strip `X4`, so the skid returns the cabinet's field. A container wires a part-ful
external strip `X9` to the skid's strip.

The bug: author-0032 accepted the pass-through (no `UNIT_BOUNDARY_BYPASSED`) but the layout drew
a passed-through connector only. A strip's terminals drew in no set, so `fr.write` raised one
`CONNECTION_NOT_DRAWN` per wire on the container's and the skid's documents. The rule (decision
layout-0162, amending layout-0160 from connectors to every boundary function): in one drawing
set the outermost unit drawn as a black box that has the function on its boundary draws it. The
print is the real path from the document's unit: `-U5-U2-X4` on the container's page. The skid
wires nothing to the strip, so its own set draws no box cell for it (layout-0214: a box cell the
parent does not wire is a loose terminal). The cabinet's own document draws no `-X4`: no wire
inside it reaches the strip, so only its terminal table lists it (L7,
layout-0202, which amends the cabinet's local print).
Its schematic then has nothing to draw and adds no page, and no `DOCUMENT_NO_DRAWINGS` fires
while the table page stands (pdf-0033).
"""

import re
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_model import derive
from fransys_model.layout import DrawingSet, Page, layout_of

_REL: dict[str, Any] = {"revision": 1, "interface_version": 1, "date": "2026-01-01"}


class _Io(NamedTuple):
    X4: Any


@fr.unit("demo-strip-cab", text="first", by="AB", **_REL)
def _cab(u: Any) -> _Io:
    return _Io(u.terminal_strip("X4", "DEMO-TB-2.5", 2, interface=True))


@fr.unit("demo-strip-skid", text="first", by="AB", **_REL)
def _skid(u: Any) -> _Io:
    return _Io(u.add(_cab, "U2").X4)


@fr.unit("demo-strip-top", text="first", by="AB", **_REL)
def _top(u: Any) -> _Io:
    skid = u.add(_skid, "U5")
    x9 = u.terminal_strip("X9", "DEMO-TB-2.5", 2, external=True)
    u.detail.wire(skid.X4[1], x9[1].outer, wire=(BU, 0.5))
    u.detail.wire(skid.X4[2], x9[2].outer, wire=(BU, 0.5))
    return _Io(x9)


def _errors(result: fr.BuildResult) -> list[str]:
    return [f.code for f in result.findings if f.severity.name == "ERROR"]


class _Written(NamedTuple):
    top: list[str]
    skid: list[str]


@pytest.fixture(scope="module")
def written() -> _Written:
    root = Path(tempfile.mkdtemp())
    d = fr.design("demo_parts")
    d.add(_top, "C1", place=None)
    docs = []
    for stem, name in (
        ("top", "demo-strip-top"),
        ("skid", "demo-strip-skid"),
    ):
        (root / f"{stem}.md").write_text(f"# {stem}\n", encoding="utf-8")
        docs.append(
            fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, name, cover=root / f"{stem}.md")
        )
    result = fr.build(d, *docs)
    assert _errors(result) == []
    fr.write(result, root / "out", intermediates=root / "inter")
    model = result.model
    names = {derive.unit_release(model, u).name: u for u in derive.units(model)}
    sets = layout_of(model, DrawingSet)

    def texts(name: str) -> list[str]:
        found: list[str] = []
        for page in layout_of(model, Page).values():
            if sets[page.drawing_set].unit == names[name]:
                svg = (root / "inter" / f"layout.page-{page.id.value}.svg").read_text("utf-8")
                found += re.findall(r">([^<>]+)</text>", svg)
        return found

    return _Written(texts("demo-strip-top"), texts("demo-strip-skid"))


def test_the_container_prints_the_real_path(written: _Written) -> None:
    assert any(t.startswith("-U5-U2-X4") for t in written.top)


def test_the_skid_draws_no_box_cell_it_does_not_wire(written: _Written) -> None:
    """layout-0214; the container, which wires the strip, still prints it (test above)."""
    assert any(t.startswith("-U5-U2-X4") for t in written.top)
    assert [t for t in written.skid if "X4" in t] == []


def test_the_pass_through_has_no_connection_error(tmp_path: Path) -> None:
    d = fr.design("demo_parts")
    d.add(_top, "C1", place=None)
    (tmp_path / "skid.md").write_text("# skid\n", encoding="utf-8")
    skid = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC, "demo-strip-skid", cover=tmp_path / "skid.md"
    )
    assert _errors(fr.build(d, skid)) == []


def test_the_skid_document_builds_without_the_unwired_strip(tmp_path: Path) -> None:
    """layout-0214 with pdf-0033: no `-U2-X4:1` box cell, no "No drawings." and no error."""
    d = fr.design("demo_parts")
    d.add(_top, "C1", place=None)
    (tmp_path / "skid.md").write_text("# skid\n", encoding="utf-8")
    skid = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC, "demo-strip-skid", cover=tmp_path / "skid.md"
    )
    result = fr.build(d, skid)
    assert _errors(result) == []
    fr.write(result, tmp_path / "out", intermediates=tmp_path / "im")
    source = (tmp_path / "im" / "skid.typ").read_text(encoding="utf-8")
    assert "-U2-X4:1" not in source
    assert "No drawings." not in source


def test_the_cabinet_prints_the_strip_locally(tmp_path: Path) -> None:
    """pdf-0033: the cabinet schematic has nothing to draw and adds no page; its table lists X4."""
    d = fr.design("demo_parts")
    d.add(_top, "C1", place=None)
    (tmp_path / "cab.md").write_text("# cab\n", encoding="utf-8")
    cab = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC, "demo-strip-cab", cover=tmp_path / "cab.md"
    )
    result = fr.build(d, cab)
    assert "DOCUMENT_NO_DRAWINGS" not in _errors(result)
    fr.write(result, tmp_path / "out", intermediates=tmp_path / "im")
    source = (tmp_path / "im" / "cab.typ").read_text(encoding="utf-8")
    assert "No drawings." not in source
    assert "X4" in source
