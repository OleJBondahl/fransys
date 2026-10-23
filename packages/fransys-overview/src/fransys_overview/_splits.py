"""The colour splits, Python's list: ids, order, picker names and the class slot each owns (O10).

`_data._classes` fills a box's `cls` by `classes_of`, in `CLASS_SPLITS` order. The page script keeps
its own `SPLITS` and `SPLIT_AT` (overview-0014); a test pins that they equal this list.
"""

from typing import Final

NONE_SPLIT: Final[str] = "none"
SPLITS: Final[tuple[tuple[str, str], ...]] = (
    (NONE_SPLIT, "Nothing"),
    ("unit", "Unit"),
    ("group", "Function group"),
    ("kind", "Item kind"),
    ("location", "Location"),
)
CLASS_SPLITS: Final[tuple[str, ...]] = tuple(split for split, _ in SPLITS[1:])


def classes_of(**by_split: str | None) -> list[str | None]:
    """A box's class in each split, in `CLASS_SPLITS` order; a split with no value raises."""
    return [by_split[split] for split in CLASS_SPLITS]
