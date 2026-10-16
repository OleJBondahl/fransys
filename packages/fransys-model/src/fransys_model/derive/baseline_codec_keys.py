"""The item-key fields of a version-2 listing, written and read beside the v1 ones (model-0300)."""

from typing import Any
lazy from collections.abc import Mapping

lazy from fransys_kernel import JsonValue

from .revision_text import revision_text
lazy from .rows_baseline import Listing

ITEM_KEYS = ("key",)
BOUNDARY_KEYS = ("key", "pin")
END_KEYS = ("a_key", "a_pin", "b_key", "b_pin")
NET_KEYS = ("port_keys", "port_pins")


def key_fields(row: object, names: tuple[str, ...]) -> dict[str, JsonValue]:
    """`row`'s key fields among `names` that are set; none for a v1 row, so its bytes stay."""
    out: dict[str, JsonValue] = {}
    for name in names:
        value = getattr(row, name)
        if value is None or value == ():
            continue
        out[name] = list(value) if isinstance(value, tuple) else value
    return out


def key_kwargs(data: Mapping[str, object], names: tuple[str, ...]) -> dict[str, Any]:
    """The key fields among `names` that `data` holds, as constructor keywords; none in a v1 row."""
    return {
        name: tuple(value) if isinstance(value, list | tuple) else value
        for name in names
        if (value := data.get(name)) is not None
    }


def has_item_keys(listing: Listing) -> bool:
    """Whether every item row of `listing` has its key: a v2 listing; no items counts as yes."""
    return all(row.key is not None for row in listing.items)


def keyless_release(listing: Listing) -> str | None:
    """The `name V.R` of a keyless `listing`'s release, else `None` (CHANGES_BY_NAME)."""
    if has_item_keys(listing):
        return None
    unit = listing.unit
    return f"{unit.name} {revision_text(unit.version, unit.revision)}"
