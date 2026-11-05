"""Field case: 3-pole contactors in one cabinet's document wired pole by pole to motors in another's.
The bug (KI-496, closed): the bundle's one marker listed its far ports, but the checker credited no other lane's end, so
CONNECTION_NOT_DRAWN and DANGLING_WIRE_END showed. The lanes end at the one cut-end x; the checker joins them (R1351, R1352)."""

from collections import Counter

import fransys as fr
import pytest
from _drawn_pages import drawn_pages, markers_in
from _model_build_cover import unit_document
from fransys.colours import BK

_PHASES = ((2, "U"), (4, "V"), (6, "W"))
_SHAPES = ("mixed-contactors-to-one-motor", "two-contactors-in-parallel-to-one-motor", "each-contactor-to-its-motor")


def _built(shape: str) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Drive", number="D-1", customer="Demo Co", revision=1, author="XX")
    d.revision(1, date="2026-10-29", text="First issue", created="XX")
    cab, fld = d.location("CAB", "Cabinet"), d.location("FLD", "Field")
    k1, k2 = d.device("K1", "DEMO-CTR-3P-NC", place="CAB"), d.device("K2", "DEMO-CTR-3P-NC", place="CAB")
    m1, m2 = d.device("M1", "DEMO-MOTOR-4KW", place="FLD"), d.device("M2", "DEMO-MOTOR-4KW", place="FLD")
    if shape == "mixed-contactors-to-one-motor":
        pairs = [(k1.main[2], m1.motor["U"]), (k2.main[4], m1.motor["V"]), (k1.main[6], m1.motor["W"])]
    elif shape == "two-contactors-in-parallel-to-one-motor":
        pairs = [(k.main[p], m1.motor[q]) for k in (k1, k2) for p, q in _PHASES]
    else:
        pairs = [(k.main[p], m.motor[q]) for k, m in ((k1, m1), (k2, m2)) for p, q in _PHASES]
    for a, b in pairs:
        d.series(a, b, wire=(BK, 2.5))
    return fr.build(d, unit_document(cab), unit_document(fld))


def _marker_count(shape: str) -> int:
    return sum(len(markers_in(drawing)) for drawing in drawn_pages(_built(shape).model).values())


@pytest.mark.parametrize("shape", _SHAPES)
def test_every_conductor_between_the_two_documents_has_a_marker_at_both_ends(shape: str) -> None:
    result = _built(shape)
    assert _marker_count(shape) > 0
    found = Counter(f.code for f in fr.check(result))
    assert (found["CONNECTION_NOT_DRAWN"], found["DANGLING_WIRE_END"]) == (0, 0)


# mixed: K1 fan (poles 2, 6) + lone K2:4 on CAB, M1 fan (U, W) + lone V on FLD; parallel: one 3-lane fan a page (2), the 6 on CAB stay KI-563.
@pytest.mark.parametrize(
    ("shape", "want"),
    [
        ("mixed-contactors-to-one-motor", 4),
        ("two-contactors-in-parallel-to-one-motor", 2),
        ("each-contactor-to-its-motor", 4),
    ],
)
def test_every_bundle_draws_one_marker_per_cut(shape: str, want: int) -> None:
    assert _marker_count(shape) == want
