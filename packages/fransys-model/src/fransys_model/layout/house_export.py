"""The house records of `[export]` and `[designation]`.

Exports are named, placed and written by the first; automatic designations start at a number
set by the second.
"""

from fransys_model.kernel import AuthoringKey, Id, Value, record

__all__ = ["CSV_QUOTINGS", "DesignationForm", "ExportForm"]

# The `csv` quoting modes `[export] csv_quoting` may name: `csv.QUOTE_<NAME>`.
CSV_QUOTINGS = ("minimal", "all", "nonnumeric", "none")


@record(kind="layout.designation", singleton=True)
class DesignationForm:
    """The `[designation]` table: the first number an automatic designation takes."""

    id: Id[DesignationForm]
    key: AuthoringKey
    number_start: int
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.export", singleton=True)
class ExportForm:
    """The `[export]` table: which reports are written, how files are named, placed and encoded.

    `csv_quoting` is the name of a `csv` quoting mode: minimal, all, nonnumeric or none.
    `hide_pe` leaves the PE rail off the drawing sheets (lists keep it).
    `ring_out_skip` lists the `DocumentPreset` values whose documents get no ring-out sheet.
    """

    id: Id[ExportForm]
    key: AuthoringKey
    reports: tuple[str, ...]
    name_join: str
    version_sign: str
    ref_sign: str
    data_dir: str
    data_suffixes: tuple[str, ...]
    csv_delimiter: str
    csv_encoding: str
    csv_quoting: str
    csv_newline: str
    hide_pe: bool
    ring_out_skip: tuple[str, ...]
    ext: frozendict[str, Value] = frozendict()
