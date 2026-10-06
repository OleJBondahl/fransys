"""A unit's baseline listing (baseline spec `docs/specs/2026-09-23-baseline.md`, L2).

Reached as `fransys_model.derive.baseline.<name>`, never re-exported from
`derive/__init__.py` (that file is a parallel task's; this module's own file set stays
disjoint from it). This module is the surface only; the code lives beside it by concern:

- `baseline_designation`: `unit_designation`, `reference_designation`'s rule with the unit's own
  common location dropped from the `+` segment, never the `=` segment (a group move changes
  what the drawings print, so it changes the release), and the cross-unit port texts.
- `baseline_listing`: `listing`, one `Listing` (the row shapes live in `derive.rows`).
  `listing(model, unit=None)` is the system listing, `Project`-sourced: `unit_designation`'s
  common location is `None` for `unit=None` by construction (`_common_location`
  short-circuits), which makes it degenerate exactly to the ordinary, full model-relative
  `reference_designation`/`printed_designation`.
- `baseline_codec`: `dumps`/`loads`, the canonical JSON codec, and `differing_sections`, which
  names the top-level fields two listings disagree on, for `REVISION_ALREADY_RELEASED` and
  `BASELINE_DIFFERS`'s messages.
- `baseline_diff`, `baseline_diff_units`, `baseline_diff_wiring`: `diff` (baseline spec M1).
"""

from .baseline_codec import differing_sections, dumps, loads
from .baseline_designation import unit_designation
from .baseline_diff import diff
from .baseline_listing import listing
from .rows import CHANGE_COLUMNS, Change, Listing, ListingDiff

__all__ = [
    "CHANGE_COLUMNS",
    "Change",
    "Listing",
    "ListingDiff",
    "diff",
    "differing_sections",
    "dumps",
    "listing",
    "loads",
    "unit_designation",
]
