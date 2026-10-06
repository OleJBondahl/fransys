"""Vocabulary: project metadata (design/vocabulary.md 6 "Project", decision 0009)."""

from fransys_model.kernel import AuthoringKey, Id, Value, record

from .release_version import refuse_below_one


@record(kind="project", singleton=True)
class Project:
    """The title-block facts every document shows; at most one per model.

    Example: `Project(title="Invented pump station", number="P-0001", ...)`. A second
    `Project` in one model is a freeze error. `version` and `revision` say which history entry
    is current; the date is that entry's, authored once on the `Revision` record and never read
    from a clock (SC4, decision model-0082: `derive.current_revision`). Both are ints of 1 or
    more, refused when the record is made (`release_version`, FD4); they print as
    `derive.revision_text` (`1.3`). `notice` is the title
    block's IP notice cell text, written by `d.project(notice=...)`; the default `""` fills an
    empty cell (spec page-frame R11.4, decision model-0051).
    """

    id: Id[Project]
    key: AuthoringKey
    title: str
    number: str
    customer: str
    revision: int
    author: str
    notice: str = ""
    version: int = 1
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Refuse a `version` or `revision` below 1; other types are `freeze()`'s."""
        refuse_below_one("project", self.id, "project", "version", self.version)
        refuse_below_one("project", self.id, "project", "revision", self.revision)
