"""The house record of `[ratings]`: the budget of the rating reader's state search (model-0482)."""

from fransys_model.kernel import AuthoringKey, Id, Value, record

__all__ = ["RatingsForm"]


@record(kind="layout.ratings", singleton=True)
class RatingsForm:
    """The `[ratings]` table: `max_solves` is the most solves the current law spends on one block of items."""

    id: Id[RatingsForm]
    key: AuthoringKey
    max_solves: int
    ext: frozendict[str, Value] = frozendict()
