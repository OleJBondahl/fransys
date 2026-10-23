"""A jumper group's Bridge marks reach the written PDF as render's images (pdf-0049, render-0021).

The facade hands `fransys_render.bridge_pieces(LIBRARY)` to `fransys_pdf.source`; without it a
terminal list with a jumper group would raise. A unit whose strip is bridged through the public
API builds, writes its Typst source with the pieces placed, and compiles to a PDF.
"""

from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr


class _Io(NamedTuple):
    X4: Any


@fr.unit(
    "demo-feed",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first",
    by="AB",
    title="Feed",
    number="N-1",
)
def _feed(d: Any) -> _Io:
    x4 = d.terminal_strip("X4", "DEMO-TB-2.5", 6, bridged=(2, 6))
    with d.function("DRV", "Drives"):
        d.detail.wire(x4[2], d.device("S1", "DEMO-PB-NC").sw["A"], wire=("RD", 0.75))
    return _Io(x4)


def test_a_bridged_strip_writes_its_marks_as_placed_images(tmp_path: Path) -> None:
    d = fr.design("demo_parts")
    d.add(_feed, "U1")
    cover = tmp_path / "cover.md"
    cover.write_text("# cover\n", encoding="utf-8")
    built = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-feed", cover=cover))
    work = tmp_path / "work"
    work.mkdir()
    written = fr.write(built, tmp_path / "out", intermediates=work)
    source = "".join(p.read_text(encoding="utf-8") for p in work.glob("*.typ"))
    assert 'width=\\"3.0mm\\" height=\\"1.0mm\\"' in source  # render's lane line, placed
    assert 'width=\\"2.0mm\\" height=\\"1.0mm\\"' in source  # and its tick
    assert "line(start" not in source
    assert any(path.suffix == ".pdf" for path in written)
