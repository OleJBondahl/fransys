"""Whether a stored listing still holds: `listing_status` (LS2, LS3, model-0289).

The comparison runs under the rules of the release that cut the stored text, so a rule that moved
since is told apart from a change of the unit. Pure: takes values, reads no file.
"""

from dataclasses import dataclass
from typing import Literal

lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Unit

from .baseline_codec import differing_sections, loads, matches, stored_version
from .baseline_listing import listing
from .baseline_rules import CURRENT, holder_rule_release, listing_rules, rules_moved_in
from .baseline_unchecked import leave_out
lazy from .rows_baseline import Listing

State = Literal["same", "rules_moved", "rows_unchecked", "differs", "too_old"]


@dataclass(frozen=True, slots=True)
class ListingStatus:
    """How a stored listing relates to the model's fresh one.

    `same`: equal under today's rules. `rules_moved`: equal under the rules that cut it, so only
    a rule moved, in the release(s) `moved_in` names. `rows_unchecked`: equal in every row the
    stored rules can rebuild; `unchecked` rows hold a contact block numbered before `moved_in`
    and were left out. `differs`: the unit changed; `sections` are the top-level sections that
    differ, `against` the stored and `compared` the fresh listing without the left-out rows.
    `too_old`: no rules known for it.
    """

    state: State
    sections: tuple[str, ...] = ()
    moved_in: str = ""
    unchecked: int = 0
    compared: Listing | None = None
    against: Listing | None = None


def listing_status(
    stored_text: str, model: Model, unit: Id[Unit] | None, fransys_version: str
) -> ListingStatus:
    """`stored_text` against `unit`'s listing, under the rules `fransys_version` cut it by."""
    rules = listing_rules(stored_version(stored_text), fransys_version)
    if rules is None:
        return ListingStatus("too_old")
    fresh = listing(model, unit)
    if matches(stored_text, fresh):
        return ListingStatus("same")
    old = fresh if rules == CURRENT else listing(model, unit, rules)
    against, compared, unchecked = leave_out(loads(stored_text), old)
    if sections := differing_sections(against, compared):
        return ListingStatus("differs", sections, compared=compared, against=against)
    if unchecked:
        moved_in = holder_rule_release()
        return ListingStatus("rows_unchecked", moved_in=moved_in, unchecked=unchecked)
    moved_in = rules_moved_in(rules)
    return ListingStatus("rules_moved", moved_in=moved_in)
