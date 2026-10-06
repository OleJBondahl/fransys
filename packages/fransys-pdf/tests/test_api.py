import fransys_pdf

from fransys_model.vocab import PageKind


def test_public_names():
    assert sorted(fransys_pdf.__all__) == [
        "PRESET_PAGES",
        "check",
        "document_pages",
        "font_dir",
        "page_kinds",
        "requests_harness_pages",
        "source",
    ]


def test_requests_harness_pages_is_true_for_exactly_the_two_cable_page_kinds():
    """`CONTENTS` or `HARNESS_DRAWING` alone is enough; every other page kind is not (pdf-0015)."""
    cable_kinds = {PageKind.CONTENTS, PageKind.HARNESS_DRAWING}
    assert fransys_pdf.requests_harness_pages((PageKind.COVER, PageKind.CONTENTS))
    assert not fransys_pdf.requests_harness_pages(())
    for kind in PageKind:
        assert fransys_pdf.requests_harness_pages((kind,)) == (kind in cable_kinds), kind


def test_font_dir_is_the_packaged_fonts_directory():
    """`font_dir()` names the path without reading it (P2): the directory need not exist yet."""
    path = fransys_pdf.font_dir()
    assert path.name == "fonts"
    assert path.parent.name == "fransys_pdf"
