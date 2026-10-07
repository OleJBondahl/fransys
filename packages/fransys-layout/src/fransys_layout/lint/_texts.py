"""`TEXT_CROSSED_BY_ROUTE` and `TEXT_OVERLAP`, private to the geometric lint (F7, layout-0047).

The designer's review metric `text_crossed_by_route` is the union of two codes, one defect
each, never both:

- a *route* run through a label box or a marker box is `WIRE_OVER_LABEL` (`geometric._wires`);
- a link marker's *stub* run through a text box is this code.

The stub is the conductor from the marker's port to its box, which render draws as part of the
marker glyph. It is not stored in the `Layout`, so nothing else can see it; it is rebuilt here
from `LinkMarker.at`, `LinkMarker.turn` and `LinkMarker.box`, the way render draws it (marker
glyphs in `fransys_render/_markers.py`: one line from the port, or from `turn`, to the box;
for a box beside its stub, beyond a sibling lane, the stub down to the box's near edge and the
lead along that edge to its near corner).

`text_overlaps` is the designer's review metric of the same name: two texts of one page whose
boxes overlap, or a text's box overlapping a symbol body it is not the tag of.
"""

from itertools import combinations
from typing import TYPE_CHECKING

from fransys_layout.geometry import overlaps
from fransys_layout.stages.space import crosses
from fransys_layout.stages.stub_runs import stub_runs
from fransys_model.kernel import Finding, Severity

from .codes import TEXT_CROSSED_BY_ROUTE, TEXT_OVERLAP

if TYPE_CHECKING:
    from fransys_layout.geometry import Box
    from fransys_layout.stages import Handle, LinkMarker, PlacedFunction, PlacedLabel


def text_crossings(
    labels: tuple[PlacedLabel, ...], markers: tuple[LinkMarker, ...]
) -> list[Finding]:
    """One `TEXT_CROSSED_BY_ROUTE` per (marker, text) pair whose stub runs through the text."""
    texts = [
        *((label.subject, label.box) for label in labels),
        *((marker.port, marker.box) for marker in markers if marker.lead and not marker.symbol),
    ]
    found: dict[tuple[Handle, ...], Finding] = {}
    for marker in (one for one in markers if not one.symbol):  # a power end draws no stub
        runs = stub_runs(marker)
        for subject, box in texts:
            if any(crosses(box, run) for run in runs):
                finding = Finding(
                    code=TEXT_CROSSED_BY_ROUTE,
                    severity=Severity.WARNING,
                    subjects=(marker.connection, marker.port, subject),
                    message="a link marker's stub runs through a text box",
                )
                found.setdefault(finding.subjects, finding)
    return [found[subjects] for subjects in sorted(found)]


def text_overlaps(
    labels: tuple[PlacedLabel, ...],
    markers: tuple[LinkMarker, ...],
    bodies: tuple[tuple[PlacedFunction, Box], ...],
    ink: tuple[tuple[Handle, Box], ...] = (),
) -> list[Finding]:
    """One `TEXT_OVERLAP` per pair of texts, or text and foreign body, that share interior.

    `ink` holds a harness line's label, stub and connector boxes, each checked against bodies too.
    """
    texts = [
        *((label.subject, label.box) for label in labels),
        *((marker.port, marker.box) for marker in markers if marker.lead and not marker.symbol),
        *ink,
    ]
    drawn = {subject for subject, _ in ink}
    found: dict[tuple[Handle, Handle], Finding] = {}

    def _fire(a: Handle, b: Handle, message: str) -> None:
        subjects = (a, b) if a < b else (b, a)
        found.setdefault(
            subjects,
            Finding(
                code=TEXT_OVERLAP, severity=Severity.WARNING, subjects=subjects, message=message
            ),
        )

    for (subject, box), (other, other_box) in combinations(texts, 2):
        if overlaps(box, other_box):
            _fire(subject, other, "two texts on the page overlap")
    for subject, box in texts:
        if subject.kind != "function" and subject not in drawn:
            continue
        for function, body in bodies:
            if subject != function.function and overlaps(box, body):
                _fire(
                    subject,
                    function.function,
                    "a text overlaps a symbol body it does not belong to",
                )
    return [found[subjects] for subjects in sorted(found)]
