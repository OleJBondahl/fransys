"""Field case: a cover too tall for its page stops the write, found by Typst measuring the page.

The engineering shape: a cabinet document whose cover text is long (a scope description of many
paragraphs) and whose revision history stands on the page foot under it.

The bug (pdf-0010): `COVER_OVERFLOW` was a character-count estimate in `check`, a WARNING, with a
line pitch and a table inset kept in step with Typst by hand (the pitch drifted once, pdf-0038).
A write went on and printed a cover whose text ran into the revision table. The rule (decision
pdf-0047, 0211): the cover source measures its own text block and table at write; Typst panics
when they would overlap, the write raises `BuildErrors` naming the document and both heights,
and no file is written. `fr.check` no longer reports it.
"""

lazy from pathlib import Path

import fransys as fr
import pytest

_PARAGRAPH = "The cabinet feeds the demo skid and carries its own lamp, relay and terminal strip."


def _build(root: Path, paragraphs: int):
    root.mkdir(parents=True, exist_ok=True)
    d = fr.design("demo_parts", place="C1")
    d.project(title="Cabinet", number="CAB-1", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-16", text="First issue", created="XX")
    cabinet = d.location("C1", "Cabinet")
    d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    cover = root / "cover.md"
    body = "\n\n".join([_PARAGRAPH] * paragraphs)
    cover.write_text(f"# Cabinet\n\n{body}\n", encoding="utf-8")
    document = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC,
        cabinet,
        cover=cover,
        remove=(fr.PageKind.SCHEMATIC,),
    )
    return fr.build(d, document)


def test_a_cover_taller_than_the_page_stops_the_write_and_names_the_heights(tmp_path):
    result = _build(tmp_path, paragraphs=60)
    out = tmp_path / "out"
    with pytest.raises(fr.BuildErrors) as raised:
        fr.write(result, out_dir=out)
    text = str(raised.value)
    assert "COVER_OVERFLOW" in text
    assert "cover text" in text
    assert "revision table" in text
    assert "mm" in text
    assert "subject:" in text  # the document is named
    assert "shorten the cover file or the revision table" in text.lower()
    assert not list(out.glob("*"))  # nothing written


def test_a_short_cover_writes_and_check_reports_no_overflow(tmp_path):
    result = _build(tmp_path, paragraphs=2)
    assert "COVER_OVERFLOW" not in [f.code for f in fr.check(result)]
    written = fr.write(result, out_dir=tmp_path / "out")
    assert [p.suffix for p in written].count(".pdf") == 1


def test_the_limit_is_the_boundary_between_33_and_34_paragraphs(tmp_path):
    """One paragraph (about 7 mm) tips the page over: the measure is exact, not a margin."""
    fits = _build(tmp_path / "fits", paragraphs=33)
    assert fr.write(fits, out_dir=tmp_path / "fits-out")
    over = _build(tmp_path / "over", paragraphs=34)
    with pytest.raises(fr.BuildErrors, match="COVER_OVERFLOW"):
        fr.write(over, out_dir=tmp_path / "over-out")
