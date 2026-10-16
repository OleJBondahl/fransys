"""`score(scene)`: the terms of the placement objective that a scene states (design section 3).

One counter per term. The same function scores today's output, a mock-up and the engine.
This is the one home of the crossing rule: once per point and per pair of nets. Cable lines and
fan legs of the harness family are outside its scope (design fact 18).
"""

from collections import Counter
from typing import TYPE_CHECKING

from .outputs import Score
from .score_facts import attached_off_pin, head_off_legs, row_broken
from .score_placement import junction_off_line, loose, pair_cut
from .score_wiring import wiring

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .outputs import Scene

# Research E3 sets these. They move into Options when a stage reads Q.
WEIGHTS = frozendict(
    {
        "tag": 1.0,  # inside w_ref: a tag pair
        "arrow": 0.5,  # inside w_ref: an arrow pair
        "star": 1.0,  # inside w_ref: a star marker
        "ref": 3.0,
        "x": 1.0,  # per crossing
        "b": 0.3,  # per excess bend
        "d": 1 / 64,  # per G of detour
        "p": 2.0,  # per page beyond the first
        "f": 1.0,  # per unit of squared empty fill
    }
)
R_CLASS = frozendict(
    {"tag": "tag_pair", "arrow": "arrow_pair", "star": "star", "stub": "stub", "copy": "copy"}
)


def placement_flags(scene: Scene) -> dict[str, list[str]]:
    """P1 to P6: each rule's name with the boxes or nets it flags."""
    return {
        "attached_off_pin": attached_off_pin(scene),
        "head_off_legs": head_off_legs(scene),
        "junction_off_line": junction_off_line(scene),
        "loose": loose(scene),
        "pair_cut": pair_cut(scene),
        "row_broken": row_broken(scene),
    }


def _quality(refs: frozendict[str, int], x: int, b: int, d: int, scene: Scene) -> float:
    """Q by design section 3.1; a scene with no rows has fill `()`, so its fill term is 0."""
    ref = (
        WEIGHTS["tag"] * refs.get("tag_pair", 0)
        + WEIGHTS["arrow"] * refs.get("arrow_pair", 0)
        + WEIGHTS["star"] * refs.get("star", 0)
    )
    return (
        WEIGHTS["ref"] * ref
        + WEIGHTS["x"] * x
        + WEIGHTS["b"] * b
        + WEIGHTS["d"] * d
        + WEIGHTS["p"] * max(scene.pages - 1, 0)
        + WEIGHTS["f"] * sum((1 - f) ** 2 for f in scene.fill)
    )


def score(scene: Scene, bundle_of: Mapping[str, str] | None = None) -> Score:
    """Count every term of `scene`; the crossing counter counts points.

    `bundle_of` (score_wiring.bundles) lets a member's drop cross its own bundle's trunk free.
    """
    refs = frozendict(Counter(R_CLASS[m.kind] for m in scene.markers))
    terms = wiring(scene.wires, bundle_of)
    x, b, d = terms["crossings"], terms["excess_bends"], terms["detour_g"]
    flags = placement_flags(scene)
    return Score(
        tuple(sorted((rule, len(boxes)) for rule, boxes in flags.items())),
        tuple(sorted(refs.items())),
        x,
        b,
        d,
        scene.pages,
        scene.fill,
        _quality(refs, x, b, d, scene),
    )
