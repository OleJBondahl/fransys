"""Field case: a unit group with no lower band to cut still overflows its page (layout-0234).
The bug: with no lower band the cut cut nothing, so the page ran past the content box.
Restored without a mate (R1526): only the six-coil shape builds; the two-coil outline carry needs the plug and board."""

from _drawn_pages import drawn_pages
from test_a_harness_line_on_an_overfull_page_still_routes import _built


def test_an_upper_band_taller_than_the_page_alone_stays_inside_the_content_box() -> None:
    built = _built(2, 6)
    assert [f for f in built.findings if f.severity.name == "ERROR"] == []
    # R467 Q02: the headers' set keeps its cut ends and their stubs, on a page of its own.
    pages = drawn_pages(built.model).values()
    assert len([d for d in pages if any(s.key == "make-contact" for s in d.symbols)]) == 1
