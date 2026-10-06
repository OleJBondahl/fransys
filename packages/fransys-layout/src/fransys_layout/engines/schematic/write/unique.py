"""Private to `write/`: the guard that no two derived records of one kind share a key."""

from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import LayoutError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_layout.engines.schematic.write.keys import WriteKeys
    from fransys_model.kernel import AuthoringKey, Id, Record


def check_unique(
    keys: WriteKeys, records: Iterable[Record], set_of_page: Mapping[Id[Any], AuthoringKey]
) -> None:
    """Raise a `LayoutError` naming both records when two of one kind share a key."""
    seen: dict[tuple[type, AuthoringKey], Record] = {}
    for record in records:
        first = seen.get((type(record), record.key))
        if first is None:
            seen[type(record), record.key] = record
        else:
            msg = (
                f"two {type(record).__name__} records share one key: "
                f"{_describe(keys, first, set_of_page)} and "
                f"{_describe(keys, record, set_of_page)}"
            )
            raise LayoutError(msg)


def _describe(keys: WriteKeys, record: Record, set_of_page: Mapping[Id[Any], AuthoringKey]) -> str:
    """`<subject key> in drawing set <key>`: the record's function (its key if none) and set."""
    function = getattr(record, "function", None)
    port = getattr(record, "port", None)
    if function is None and port is not None:
        function = keys.port_function[port]
    subject = keys.function[function] if function is not None else record.key
    page = getattr(record, "page", None)
    where = set_of_page[page] if page is not None else ()
    return f"{subject} in drawing set {where}"
