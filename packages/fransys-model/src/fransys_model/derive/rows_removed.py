"""The row shape of a removed item's ancestors (OVERVIEW RC3, overview-0005)."""

from fransys_model.kernel import value


@value
class RemovedAncestry:
    """The ancestors of one removed `items` row of a `ListingDiff`, nearest first.

    `change` indexes `ListingDiff.changes`. `ancestors` are subject texts as the listing prints
    them: the item's parent chain in the earlier listing, then the listed unit's own subject.
    """

    change: int
    ancestors: tuple[str, ...]
