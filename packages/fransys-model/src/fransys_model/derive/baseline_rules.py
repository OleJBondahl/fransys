"""The listing rules a stored version-1 listing was cut under (LS2, model-0289).

A listing is compared under the rules of the release that cut it, read from that release's
`fransys` version. `ListingRules` holds one value per rule that moved; `RULES_BY_RELEASE` says
which release moved which. `listing(model, unit, rules=...)` passes each value to the ONE derive
function that governs the text: this module copies no rule.
"""

import re
from dataclasses import dataclass, fields, replace

OLDEST_VERIFIABLE = "0.13.8"
KEYED_LISTING_VERSION = 2  # the listing version that carries item keys (model-0300)


@dataclass(frozen=True, slots=True)
class ListingRules:
    """One value per listing rule that moved; the default of each is today's rule.

    `holder_designation`: a contact block prints its holder's designation (model-0222, 0.18.2).
    `bar_end_without_screw`: a bar end prints the bar alone, with no screw (model-0227, 0.18.4).
    `item_keys`: every row that names an item carries its key, version 2 (model-0300, 0.20.0).
    """

    holder_designation: bool = True
    bar_end_without_screw: bool = True
    item_keys: bool = True


CURRENT = ListingRules()


@dataclass(frozen=True, slots=True)
class RuleRow:
    """The rules in force from the `fransys` release `first` on, up to the next row."""

    first: str
    rules: ListingRules


RULES_BY_RELEASE: tuple[RuleRow, ...] = (
    RuleRow(
        OLDEST_VERIFIABLE,
        ListingRules(holder_designation=False, bar_end_without_screw=False, item_keys=False),
    ),
    RuleRow("0.18.2", ListingRules(bar_end_without_screw=False, item_keys=False)),
    RuleRow("0.18.4", ListingRules(item_keys=False)),
    RuleRow("0.20.0", CURRENT),
)


def version_key(text: str) -> tuple[int, ...]:
    """`text`'s integer parts, so `0.13.14` sorts after `0.13.8`; `()` when it has none."""
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


def listing_rules(listing_version: int, fransys_version: str) -> ListingRules | None:
    """The rules a version-`listing_version` listing cut by `fransys_version` was written under.

    `None` when no row covers it: a release older than `OLDEST_VERIFIABLE`, an unreadable
    version, or a listing version the table does not know. The listing's own version says whether
    it carries item keys (2) or not (1). Never the current rules by default.
    """
    key = version_key(fransys_version)
    if (
        listing_version not in (1, KEYED_LISTING_VERSION)
        or not key
        or key < version_key(OLDEST_VERIFIABLE)
    ):
        return None
    found = RULES_BY_RELEASE[0].rules
    for row in RULES_BY_RELEASE:
        if version_key(row.first) <= key:
            found = row.rules
    return replace(found, item_keys=listing_version == KEYED_LISTING_VERSION)


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
