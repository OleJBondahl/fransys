"""Vendored fonts: Liberation Serif 2.1.5, four faces plus its licence (spec P2)."""

from fransys_pdf import font_dir

_FACES = (
    "LiberationSerif-Regular.ttf",
    "LiberationSerif-Bold.ttf",
    "LiberationSerif-Italic.ttf",
    "LiberationSerif-BoldItalic.ttf",
)


def test_every_face_is_present():
    names = {path.name for path in font_dir().iterdir()}
    for face in _FACES:
        assert face in names


def test_the_licence_text_is_present():
    names = {path.name for path in font_dir().iterdir()}
    assert "LICENSE" in names
    text = (font_dir() / "LICENSE").read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE" in text.upper()
