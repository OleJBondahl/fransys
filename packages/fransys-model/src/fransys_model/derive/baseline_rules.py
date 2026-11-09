"""The listing rules a stored version-1 listing was cut under (LS2, model-0289).

A listing is compared under the rules of the release that cut it, read from that release's
`fransys` version. `ListingRules` holds one value per rule that moved; `RULES_BY_RELEASE` says
which release moved which. `listing(model, unit, rules=...)` passes each value to the ONE derive
function that governs the text: this module copies no rule.
"""

import re
from dataclasses import dataclass, fields

OLDEST_VERIFIABLE = "0.13.8"
KEYED_LISTING_VERSION = 10  # keyed rows, no mate or harness line (0405); stored model schema 25 (0442), 26 (0443), 27 (0446), 28 (0448)
READABLE_LISTING_VERSIONS = (
    6,
    7,
    8,
    9,
    KEYED_LISTING_VERSION,
)  # 7 to 10 moved no listing text: 6 to 10 are one rule set (model-0289, 0428, 0442, 0443, 0446)


@dataclass(frozen=True, slots=True)
class ListingRules:
    """One value per listing rule that moved; the default of each is today's rule.

    `holder_designation`: a contact block prints its holder's designation (model-0222, 0.18.2).
    """

    holder_designation: bool = True


CURRENT = ListingRules()


@dataclass(frozen=True, slots=True)
class RuleRow:
    """The rules in force from the `fransys` release `first` on, up to the next row."""

    first: str
    rules: ListingRules


RULES_BY_RELEASE: tuple[RuleRow, ...] = (
    RuleRow(
        OLDEST_VERIFIABLE,
        ListingRules(holder_designation=False),
    ),
    RuleRow("0.18.2", CURRENT),
    RuleRow("0.19.10", CURRENT),
)


def version_key(text: str) -> tuple[int, ...]:
    """`text`'s integer parts, so `0.13.14` sorts after `0.13.8`; `()` when it has none."""
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


def listing_rules(listing_version: int, fransys_version: str) -> ListingRules | None:
    """The rules a version-`listing_version` listing cut by `fransys_version` was written under.

    `None` when no row covers it: a release older than `OLDEST_VERIFIABLE`, an unreadable
    version, or a listing version the table does not know (only 6 to 10 are). Never the current
    rules by default.
    """
    key = version_key(fransys_version)
    if listing_version not in READABLE_LISTING_VERSIONS or not key or key < version_key(OLDEST_VERIFIABLE):
        return None
    found = RULES_BY_RELEASE[0].rules
    for row in RULES_BY_RELEASE:
        if version_key(row.first) <= key:
            found = row.rules
    return found


def rules_moved_in(stored: ListingRules) -> str:
    """The release(s) that moved each rule `stored` differs on, `"0.18.2 and 0.18.4"` joined."""
    current = CURRENT
    moved = []
    for field in fields(ListingRules):
        want = getattr(current, field.name)
        if getattr(stored, field.name) == want:
            continue
        first = next(r.first for r in RULES_BY_RELEASE if getattr(r.rules, field.name) == want)
        if first not in moved:
            moved.append(first)
    return " and ".join(sorted(moved, key=version_key))


def holder_rule_release() -> str:
    """The release that moved the holder rule (a contact block prints its holder's designation)."""
    return next(row.first for row in RULES_BY_RELEASE if row.rules.holder_designation)
