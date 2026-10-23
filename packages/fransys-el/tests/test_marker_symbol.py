"""The reference marker is a library symbol the layer measures; fransys_el sets no box."""

import re
from pathlib import Path

import fransys_el
from conventions_fixtures import house
from fransys_el import options
from fransys_el.placement_views import MARKER, marker_boxes

from electrical_symbols import LIBRARY
from fransys_layout.symbols import library_symbol, marker_views

_SRC = Path(fransys_el.__file__).parent


def test_the_options_marker_is_the_layers_measure_of_the_library_symbol() -> None:
    got = options(house(), LIBRARY).marker
    assert got is not None
    flag = marker_views(library_symbol(LIBRARY, MARKER), LIBRARY)
    assert got == marker_boxes(LIBRARY)
    assert {o: got[o] for o in ("R0", "R180", "MR0", "MR180")} == {
        o: flag[o] for o in got if o in ("R0", "R180", "MR0", "MR180")
    }


def test_no_marker_or_keepout_literal_in_fransys_el_source() -> None:
    hits = [
        f"{path.name}:{n}"
        for path in sorted(_SRC.glob("*.py"))
        for n, line in enumerate(path.read_text().splitlines(), 1)
        if re.search(r"\bmarker\s*=(?!\s*marker_boxes\()|keepout\s*=|Box\(.*keepout", line)
    ]
    assert hits == []
