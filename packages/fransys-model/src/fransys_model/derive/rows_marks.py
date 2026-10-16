"""The rows of the marks a view takes from findings and from a listing diff (overview-0010, 0011).

They sit beside `rows.py`. A mark names a drawn box or line of one `ViewRows` by its index.
"""

from fransys_model.kernel import Severity, value


@value
class FindingHold:
    """One finding that counts on a mark: its index in the findings given, and its severity."""

    finding: int
    severity: Severity


@value
class FindingMark:
    """One box or line of a view that findings name.

    `at` indexes the view's `boxes`, or its `lines` when `on_line`. `held` lists each finding
    that counts there, in the order the findings reached it.
    """

    on_line: bool
    at: int
    held: tuple[FindingHold, ...]


@value
class DiffMark:
    """One box or line of a view that a `ListingDiff` marks, with the status the page prints.

    `at` indexes the view's `boxes`, or its `lines` when `on_line`. `status` is `added` or
    `changed`.
    """

    on_line: bool
    at: int
    status: str


@value
class DiffViewMarks:
    """The marks one view takes from a diff: boxes then lines by index, and the rows that marked.

    `shown` holds the indexes in `ListingDiff.changes` of the rows that marked a box or line.
    """

    marks: tuple[DiffMark, ...]
    shown: tuple[int, ...]


@value
class DiffRest:
    """One row no box or line of any view carries: its `status` and the subject text."""

    status: str
    text: str
