"""The one printed form of a revision (fixed designations FD4, schema spec SC2).

Lives in `vocab`, not `derive`, because `vocab.validators.revisions` names a revision in its
messages and `vocab` never imports `derive`; `derive.revision_text` re-exports it and every
other caller imports it from there (the pattern of `derive.closure` and `derive.external`).
"""


def revision_text(version: int, revision: int) -> str:
    """The revision as printed: `f"{version}.{revision}"`, `1.1`, `2.1`, `1.10`.

    The one home of the print form: a title block's Rev cell, a revision history row, a unit
    line's BOM `Revision` column, a black box title and a message naming a revision all call it.
    Nothing else formats the pair.
    """
    return f"{version}.{revision}"
