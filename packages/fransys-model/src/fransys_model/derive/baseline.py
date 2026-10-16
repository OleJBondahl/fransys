"""A unit's baseline listing (baseline spec `docs/archive/specs/2026-09-23-baseline.md`).

Reached as `fransys_model.derive.baseline.<name>`, never re-exported from
`derive/__init__.py` (that file is a parallel task's; this module's own file set stays
disjoint from it). This module is the surface only; the code lives beside it by concern:

- `baseline_change_text`: `change_identity`, `change_clause`: the identity and words of a `Change`.
- `baseline_designation`: `unit_designation`, `reference_designation`'s rule with the unit's own
  common location dropped from the `+` segment, never the `=` segment (a group move changes
  what the drawings print, so it changes the release), and the cross-unit port texts.
- `baseline_listing`: `listing`, one `Listing` (the row shapes live in `derive.rows`).
  `listing(model, unit=None)` is the system listing, `Project`-sourced: `unit_designation`'s
  common location is `None` for `unit=None` by construction (`_common_location`
  short-circuits), which makes it degenerate exactly to the ordinary, full model-relative
  `reference_designation`/`printed_designation`.
- `baseline_rules`: `ListingRules`, `RULES_BY_RELEASE`, `listing_rules`: the rules a stored listing
  was cut under, read from its release's `fransys` version (LS2, model-0289).
- `baseline_status`: `listing_status`, a stored listing compared under its own rules (LS3).
- `baseline_codec`: `dumps`/`loads`, the canonical JSON codec, and `differing_sections`, which
  names the top-level fields two listings disagree on, and `matches`, whether stored text equals a
  fresh listing; both ignore `parent`. `REVISION_ALREADY_RELEASED` and `BASELINE_DIFFERS` use them.
- `change_sections`: `change_sections`, the diff's rows as the sections a change note prints.
- `baseline_subjects`: `change_subjects`, the `Id` each diff row's subject text names.
- `baseline_diff`, `baseline_diff_units`, `baseline_diff_wiring`: `diff`.
"""

from .baseline_change_text import change_clause, change_identity
from .baseline_codec import differing_sections, dumps, loads, matches
from .baseline_designation import unit_designation
from .baseline_diff import diff
from .baseline_listing import listing
from .baseline_rules import (
    OLDEST_VERIFIABLE,
    RULES_BY_RELEASE,
    ListingRules,
    listing_rules,
    rules_moved_in,
)
from .baseline_status import ListingStatus, listing_status
from .baseline_subjects import change_subjects
from .change_sections import change_sections
from .rows_baseline import (
    CHANGE_COLUMNS,
    Change,
    ChangeSection,
    Listing,
    ListingDiff,
    ReleaseIdentity,
    StoredRelease,
    StoredReleases,
)
from .rows_removed import RemovedAncestry

__all__ = [
    "CHANGE_COLUMNS",
    "OLDEST_VERIFIABLE",
    "RULES_BY_RELEASE",
    "Change",
    "ChangeSection",
    "Listing",
    "ListingDiff",
    "ListingRules",
    "ListingStatus",
    "ReleaseIdentity",
    "RemovedAncestry",
    "StoredRelease",
    "StoredReleases",
    "change_clause",
    "change_identity",
    "change_sections",
    "change_subjects",
    "diff",
    "differing_sections",
    "dumps",
    "listing",
    "listing_rules",
    "listing_status",
    "loads",
    "matches",
    "rules_moved_in",
    "unit_designation",
]
