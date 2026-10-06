"""D3, the text placer: every text of a page in one key order, each at its first free candidate.

One function, `place_texts`, for every kind. It ranks nothing itself: each text's list comes
from `candidates.ranked_candidates`, the ranking `place` reserves from (S2). The placer is
greedy and never moves a text it has placed (D1, Room: nothing is shifted after `texts`).
"""

from typing import TYPE_CHECKING, Any
lazy from collections.abc import Sequence

from fransys_layout.geometry import Box, Facing, LayoutError, Point, overlaps
from fransys_layout.stages.space import Run, covers, crosses
from fransys_model.kernel import Finding, Id, Severity, value

from .candidates import PRIORITY, TextKind, box_of, ranked_candidates

if TYPE_CHECKING:
    from fransys_layout.stages.space import Shape, Space
    from fransys_layout.stages.types import Handle

    from .candidates import CandidateTable

LABEL_UNPLACED = "LABEL_UNPLACED"

# The message of a text with no free candidate, by kind: today's, so a stage moved onto the
# placer keeps its findings. A kind not listed takes the slot labels' message.
_UNPLACED = frozendict(
    {
        TextKind.REFERENCE: "no free place in the marker's row",
        TextKind.STUB: "no free place in the marker's row",
        TextKind.POWER: "no free place beside the power symbol",
    }
)
_UNPLACED_SLOT = "no free place beside the slot"


@value
class Place:
    """S20: one place a link marker may take: its box and its stub's boxes (WIRE-X56)."""

    box: Box
    stub: tuple[Box, ...] = ()
    fits: bool = True


@value
class Anchor:
    """One placed thing a text may stand beside, in page coordinates (docs/design/labels.md 6.7)."""

    box: Box
    facing: Facing | None = None
    fits: bool = True


@value
class TextToPlace:
    """One text of a page, not yet placed: what its ranked list and key need (D2, D3, S20)."""

    kind: TextKind
    handle: Id[Any]
    slot: str = ""
    position: Point
    width: int
    height: int
    anchors: tuple[Anchor, ...]
    own: tuple[Id[Any], ...] = ()
    places: tuple[Place, ...] = ()
    rank: int = 0


@value
class PlacedText:
    """A text at its page box. `unplaced`: no candidate was free, and its first one stands."""

    kind: TextKind
    handle: Id[Any]
    slot: str
    box: Box
    unplaced: bool = False
    index: int = 0


def place_texts(
    texts: tuple[TextToPlace, ...],
    space: Space,
    table: CandidateTable,
    *,
    lanes: tuple[Shape, ...] = (),
    runs: tuple[Run, ...] = (),
) -> tuple[tuple[PlacedText, ...], tuple[Finding, ...]]:
    """D3: every text of one page, in key order, each at its first free candidate (greedy)."""
    placed: list[PlacedText] = []
    stubs: list[tuple[Handle, Box]] = []
    findings: list[Finding] = []
    seen: set[tuple[TextKind, Handle, str]] = set()
    for text in sorted(texts, key=_key):
        if (text.kind, text.handle, text.slot) in seen:
            msg = "two texts to place share one kind, handle and slot"
            raise LayoutError(msg)
        seen.add((text.kind, text.handle, text.slot))
        blockers = [
            *(shape.box for shape in space.shapes if shape.owner not in text.own),
            *(one.box for one in placed),
        ]
        # the texts of one handle stand along one stub: theirs cross each other's boxes
        crossing = [*blockers, *(box for handle, box in stubs if handle != text.handle)]
        foreign = [one.box for one in placed if one.handle != text.handle]
        others = [_run(shape.box) for shape in lanes if shape.owner not in text.own]
        options = _options(text, table)
        index = next(
            (
                i
                for i, (place, fits) in enumerate(options)
                if fits
                and space.holds(place.box)
                and _free(place.box, crossing, others, runs)
                and not any(overlaps(part, box) for part in place.stub for box in foreign)
            ),
            None,
        )
        unplaced = index is None
        if index is None:
            index = 0
            findings.append(
                Finding(
                    code=LABEL_UNPLACED,
                    severity=Severity.WARNING,
                    subjects=(text.handle,),
                    message=_UNPLACED.get(text.kind, _UNPLACED_SLOT),
                )
            )
        place = options[index][0]
        stubs.extend((text.handle, box) for box in place.stub)
        placed.append(
            PlacedText(
                kind=text.kind,
                handle=text.handle,
                slot=text.slot,
                box=place.box,
                unplaced=unplaced,
                index=index,
            )
        )
    return tuple(placed), tuple(findings)


def _options(text: TextToPlace, table: CandidateTable) -> list[tuple[Place, bool]]:
    """The text's candidates in order, each with whether its anchor `fits`."""
    if text.places:
        return [(place, place.fits) for place in text.places]
    size = (text.width, text.height)
    return [
        (Place(box=box_of(candidate, anchor.box, size)), anchor.fits)
        for anchor in text.anchors
        for candidate in ranked_candidates(text.kind, anchor.facing, size, table)
    ]


def _key(text: TextToPlace) -> tuple[int, int, int, int, Handle, str]:
    """D3's key order: priority, the call's rank (S20), position, handle, then the slot."""
    return (
        PRIORITY[text.kind],
        text.rank,
        text.position.x,
        text.position.y,
        text.handle,
        text.slot,
    )


def _free(box: Box, blockers: Sequence[Box], lanes: Sequence[Run], runs: tuple[Run, ...]) -> bool:
    """Whether `box` overlaps no blocker, covers no lane (when it has an area), crosses no run."""
    if any(overlaps(box, blocker) for blocker in blockers):
        return False
    if box.width > 0 and box.height > 0 and any(covers(box, lane) for lane in lanes):
        return False
    return not any(crosses(box, run) for run in runs)


def _run(extent: Box) -> Run:
    """A lane's extent, a box with no width or no height, as the run it is."""
    return Run(x=extent.x, y=extent.y, to_x=extent.x + extent.width, to_y=extent.y + extent.height)
