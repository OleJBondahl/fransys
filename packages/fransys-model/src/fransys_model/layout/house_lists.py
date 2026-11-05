"""The house record of the `[lists.<name>]` tables: the columns each list prints."""

from fransys_model.kernel import AuthoringKey, Id, Value, record

__all__ = ["Lists"]


@record(kind="layout.lists", singleton=True)
class Lists:
    """The `[lists]` tables: per list name, its columns in order and how each is headed.

    `columns` holds the row field names; `pdf_words` and `csv_words` hold, in the same order, the
    `[words]` keys of each column's PDF heading and CSV header. `pdf_columns` holds only the
    lists whose PDF prints fewer fields than the CSV.
    """

    id: Id[Lists]
    key: AuthoringKey
    columns: frozendict[str, tuple[str, ...]]
    pdf_words: frozendict[str, tuple[str, ...]]
    csv_words: frozendict[str, tuple[str, ...]]
    pdf_columns: frozendict[str, tuple[str, ...]]
    ext: frozendict[str, Value] = frozendict()
