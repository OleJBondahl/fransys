"""Vendored fonts: DejaVu Sans Condensed 2.37, four faces plus its licence."""

from fransys_pdf import font_dir

_FACES = (
    "DejaVuSansCondensed.ttf",
    "DejaVuSansCondensed-Bold.ttf",
    "DejaVuSansCondensed-Oblique.ttf",
    "DejaVuSansCondensed-BoldOblique.ttf",
)


def test_every_face_is_present():
    names = {path.name for path in font_dir().iterdir()}
    for face in _FACES:
        assert face in names


def test_the_licence_text_is_present():
    names = {path.name for path in font_dir().iterdir()}
    assert "LICENSE" in names
    text = (font_dir() / "LICENSE").read_text(encoding="utf-8")
    assert "Bitstream" in text
