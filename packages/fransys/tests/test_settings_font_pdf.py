"""A consumer font is the font of the PDF: Typst reads the folder of the build's faces (ST5)."""

import re
from pathlib import Path

import fransys as fr
import fransys_author
import pytest

from fransys_model.vocab import DocumentPreset, PageKind

pytestmark = pytest.mark.wp("facade")

FONTS = Path(__file__).parent / "fixtures" / "fonts"


def _pdf(tmp_path: Path, settings: fr.Settings) -> bytes:
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    c1 = design.location("C1", "Demo cabinet")
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Demo cabinet\n\nText set in the build's font.\n", encoding="utf-8")
    document = fr.document(
        DocumentPreset.CABINET_SCHEMATIC, c1, cover=cover, remove=(PageKind.SCHEMATIC,)
    )
    result = fr.build(parts, design.draft(), document, settings=settings)
    (pdf,) = (p for p in fr.write(result, tmp_path / "out") if p.suffix == ".pdf")
    return pdf.read_bytes()


def _faces(pdf: bytes) -> set[str]:
    return {name.decode() for name in re.findall(rb"/BaseFont\s*/[A-Z]{6}\+([\w-]+)", pdf)}


def test_the_fixture_font_is_the_pdf_font_and_the_house_font_is_not(tmp_path: Path) -> None:
    toml = tmp_path / "fransys.toml"
    toml.write_text(
        f'[font]\nfiles = ["{FONTS / "DejaVuSans.ttf"}", "{FONTS / "DejaVuSans-Bold.ttf"}"]\n',
        encoding="utf-8",
    )
    ours = {name for name in _faces(_pdf(tmp_path, fr.settings())) if name.startswith("DejaVu")}
    theirs = {
        name for name in _faces(_pdf(tmp_path, fr.settings(toml))) if name.startswith("DejaVu")
    }
    assert ours
    assert theirs
    assert all("Condensed" in name for name in ours)
    assert not any("Condensed" in name for name in theirs)
