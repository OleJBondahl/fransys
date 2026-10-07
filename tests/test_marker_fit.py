"""D2/D8: every `layout.link_marker` of every golden fits inside its own stored box, padded.

`fransys_layout.engines.schematic.write.markers.link_markers` writes
`width`/`height` from the box the layout stage already reserved
(`stages/references/marker_boxes.py`'s `marker_box`), never a
re-measurement (decision `model-0037`, render D8's corrected sentence). This
is the guarantee
the feature exists for: `fransys_model.derive.drawing_text.marker_text`'s reader, measured
with `fransys_layout.geometry.text_width`, must genuinely fit inside `marker.width` with
room to spare -- the profile's `2 * marker_padding`'s worth, on every edge (decision
layout-0043's amendment, owner ruling 2026-09-23: the text must sit inside its box, clear of
every rule, not touching the outline). `marker.height` must equal the profile's
`text_height + 2 * marker_padding` exactly (`marker_box` sets `box.height` directly from
those two profile fields, never measures it). A marker text of several lines (a reference's
branch list of more than three positions, or a reference merged with an off stub, layout-0053)
is measured a line at a time: its width is its widest line's, its height one `text_height` per
line plus the padding (`star_markers.marker` and `off_markers._with_off` grow the box that way).

Every golden in `packages/fransys-layout/tests/golden/` is loaded and checked, not just the
two-location one added alongside this test: `cabinet_laid_out.json` has seven markers and
`cabinet_narrow_laid_out.json` has eight (each count is that golden's own explicit, named
claim; the wide golden's seven are all branch/reference star markers, the narrow golden's eight
mix star and plain ones), and `cabinet_two_location_laid_out.json` has eleven: five branches,
two references and four off stubs. Every marker is turned (S20 M1, M7: a box along its wire),
so its stored width and height are its long and short side swapped: the check reads a box's
"along" (the wire's direction) and "across" sides, not `width` and `height`.
"""

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_layout.engines.schematic.read.reading import profile_and_sheet
from fransys_layout.geometry import text_width
from fransys_layout.stages.references.marker_boxes import reference_box_width
from fransys_model.derive.drawing_text import marker_text
from fransys_model.kernel import loads
from fransys_model.layout import (
    LinkMarker,
    Page,
    Profile,
    StarKind,
    layout_of,
)

if TYPE_CHECKING:
    from fransys_model.kernel import Model

_GOLDEN_DIR = (
    Path(__file__).resolve().parent.parent / "packages" / "fransys-layout" / "tests" / "golden"
)

# Every `*_laid_out.json` golden, and its own marker count, named explicitly (spec X5's "never
# iterated silently" pattern): a future golden that adds markers and forgets this dict fails the
# coverage check below instead of being silently skipped.
_EXPECTED_MARKER_COUNTS: dict[str, int] = {
    "cabinet_laid_out.json": 6,
    "cabinet_narrow_laid_out.json": 8,
    "cabinet_two_location_laid_out.json": 8,
}


def _sides(marker: LinkMarker) -> tuple[int, int]:
    """`(along, across)`: the box's text-reading side and its other side (S20 M1).

    A turned box (`vertical`) reads along its height; an upright one along its width.
    """
    return (marker.height, marker.width) if marker.vertical else (marker.width, marker.height)


def _resized(marker: LinkMarker, *, along: int, across: int) -> LinkMarker:
    """`marker` with the given `_sides`, whichever way it is turned."""
    if marker.vertical:
        return replace(marker, height=along, width=across)
    return replace(marker, width=along, height=across)


def _profile_numbers(model: Model) -> tuple[int, int]:
    """The model's own authored `layout.profile.text_height`/`marker_padding`, or the defaults."""
    profiles = layout_of(model, Profile)
    if profiles:
        profile = next(iter(profiles.values()))
        return profile.text_height, profile.marker_padding
    return DEFAULT_PROFILE.text_height, DEFAULT_PROFILE.marker_padding


def _measured_size(
    model: Model, marker: LinkMarker, *, text_height: int, padding: int
) -> tuple[int, int]:
    """The box `marker_text`'s lines need, padded: widest line wide, a `text_height` per line high.

    A line at a time, since `text_width` measures one line and charges a newline as a glyph.
    """
    lines = marker_text(model, marker).split("\n")
    width = max(text_width(line, height=text_height) for line in lines) + 2 * padding
    return width, len(lines) * text_height + 2 * padding


def _is_merged_or_pure_reference(model: Model, marker: LinkMarker) -> bool:
    """Whether `marker` is a reference (LD3), not a pure, unmerged off stub (D4 excludes one).

    A plain severed pair (`star is None`) and every star/split marker (`REF`/`BRANCH`) are
    always a reference. `star is OFF` is a reference only when merged: some `BRANCH` names it
    (decision layout-0089, `_reference_group`'s own four shapes).
    """
    if marker.star is not StarKind.OFF:
        return True
    markers = layout_of(model, LinkMarker)
    return any(o.partner == marker.id and o.star is StarKind.BRANCH for o in markers.values())


def _reference_width(model: Model, *, text_height: int, padding: int) -> int:
    """RR-O5: the narrowest reference box (`#99-<position>` at the floor), as layout sizes it.

    Layout's own `reference_box_width` at its floor digits, on the model's sheet and profile. A
    run of several sets draws the box wider (the longest form), so there this is a lower bound.
    """
    profile, sheet, _ = profile_and_sheet(model)
    assert (profile.text_height, profile.marker_padding) == (text_height, padding)
    return reference_box_width(sheet, profile)


def _fits(model: Model, marker: LinkMarker, *, text_height: int, padding: int) -> bool:
    """Whether `marker`'s stored box holds the text `marker_text` reads for it, padded.

    Width is a fit (`<=`): the box was sized to the text `marker_box` measured plus
    `2 * padding`. Height is exact (`==`): `marker_box` sets
    `box.height = profile.text_height + 2 * profile.marker_padding` directly, never
    measured from the text (decision layout-0043's amendment), and each further line of a
    star marker adds one `text_height` (layout-0053).
    """
    width, height = _measured_size(model, marker, text_height=text_height, padding=padding)
    along, across = _sides(marker)
    return width <= along and across == height


def test_every_golden_is_covered_by_the_expected_marker_counts() -> None:
    """The globbed golden filenames are exactly this test's named dict, neither more nor fewer."""
    names = {path.name for path in _GOLDEN_DIR.glob("*_laid_out.json")}
    assert names == set(_EXPECTED_MARKER_COUNTS)


def test_every_marker_of_every_golden_fits_its_stored_box() -> None:
    """For every golden, every marker's measured text plus padding fits its stored width/height."""
    total = 0
    multi_line = 0
    line_stubs = 0
    for name, expected_count in _EXPECTED_MARKER_COUNTS.items():
        model = loads((_GOLDEN_DIR / name).read_text(encoding="utf-8"))
        markers = layout_of(model, LinkMarker)
        assert len(markers) == expected_count

        text_height, padding = _profile_numbers(model)
        several_sets = len({page.drawing_set for page in layout_of(model, Page).values()}) > 1
        assert padding > 0, "every golden here authors or defaults to a non-zero marker_padding"
        for marker in markers.values():
            assert _fits(model, marker, text_height=text_height, padding=padding)
            line_stubs += "line_stub" in str(marker.key)
            # Stronger than `<=` fit requires (decision layout-0089): a reference's (severed
            # pair, star or split) box is the sheet's fixed width exactly, never measured from
            # its own text (LD3 (c)) -- unless a merged off stub's own line needed more
            # (`off_markers._with_off`'s `max()`), in which case it is that wider, measured
            # value instead. A pure, unmerged off stub still gets its old exactly-measured
            # width. Either way `_fits`'s `<=` stays the correct general "fits" semantics;
            # this only gives stronger evidence of exactly which rule wrote each width.
            fixed = _reference_width(model, text_height=text_height, padding=padding)
            measured, _height = _measured_size(
                model, marker, text_height=text_height, padding=padding
            )
            along = _sides(marker)[0]
            # RR-O5: a run of several sets sizes the box for its longest form, so it is only a
            # lower bound there; one set draws the floor exactly.
            holds = (lambda a, b: a >= b) if several_sets else (lambda a, b: a == b)
            if marker.star is not StarKind.OFF:  # a plain pair, or a star REF/BRANCH
                assert holds(along, fixed)
            elif _is_merged_or_pure_reference(model, marker):  # merged: the wider of the two
                assert holds(along, max(fixed, measured))
            else:  # a pure, unmerged off stub: the old exactly-measured width
                assert along == measured
            multi_line += "\n" in marker_text(model, marker)
        total += expected_count

    assert total > 0, "every per-golden count passed by coincidence; nothing was actually checked"
    # LD5 (d), decision layout-0089: marker text is now symmetric -- every counted end of a
    # 3+-end net gets its own multi-line box (one line per OTHER end), not only the one
    # "merged" reference the old hub-and-spoke shape gave a second line to. 11 was confirmed by
    # counting `marker.height` values above one line (12 G) across the three usecase goldens;
    # V4 (layout-0099) took it from 11 to 7: -X2:1 stands over -S0's pin, so the wide and the
    # narrow cabinet each lose a branch and their star texts shrink (4, 3, 4 became 3, 0, 4).
    # C2 (model-0139) took it from 7 to 4: a marker with three or more targets prints one line.
    # HL15-HL18 (layout-0154): W1 is a harness line, not per-core markers; 4 became 6 with the
    # line stubs (one OFF stub per line leaving its page: 1 wide, 2 narrow) and the lost branches.
    assert line_stubs == 3, "the goldens' harness lines leave their pages by OFF line stubs"
    assert multi_line == 6, "LD5 (d)'s symmetric text: every 3+-end net's markers are multi-line"


def test_the_fit_check_can_fail() -> None:
    """A width one G too narrow, and a height off by one, each fail the same `_fits` check.

    In-memory `dataclasses.replace` twins of the two-location golden's two-line marker (the
    reference merged with its off stub) -- no git discard needed -- each exercising the
    identical `_fits` helper the main test above calls: one twin narrower than its own
    measured-plus-padded widest line needs (the `<=` half), one with the right width but a
    height one G over `lines * text_height + 2 * marker_padding` (the `==` half), and one
    with the one-line height (a box measured before the merge added its second line). Separate
    assertions, so a check that only shrinks `width` cannot leave the height half of `_fits`
    unproven -- a widened width alone or a loosened height comparison would still pass the
    width-only twin.
    """
    model = loads((_GOLDEN_DIR / "cabinet_two_location_laid_out.json").read_text(encoding="utf-8"))
    marker = next(m for m in layout_of(model, LinkMarker).values() if "\n" in marker_text(model, m))
    text_height, padding = _profile_numbers(model)
    assert _fits(model, marker, text_height=text_height, padding=padding)
    width, height = _measured_size(model, marker, text_height=text_height, padding=padding)
    too_narrow = _resized(marker, along=width - 1, across=height)
    assert not _fits(model, too_narrow, text_height=text_height, padding=padding)
    wrong_height = _resized(marker, along=width, across=height + 1)
    assert not _fits(model, wrong_height, text_height=text_height, padding=padding)
    one_line_high = _resized(marker, along=width, across=text_height + 2 * padding)
    assert not _fits(model, one_line_high, text_height=text_height, padding=padding)
