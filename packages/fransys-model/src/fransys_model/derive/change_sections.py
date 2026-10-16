"""A listing diff's changes grouped for a printed note: sections in order, one group per subject.

See derive-queries.md.
"""

from .rows_baseline import Change, ChangeSection, ListingDiff

# The printed order of the sections. `unit` is not here: it never becomes a section, because the
# heading and the interface line of a note are read from `ListingDiff.a` and `.b`.
_SECTION_ORDER = ("items", "units", "boundary", "conductors", "mates", "nets")


def _subject_groups(rows: list[Change]) -> tuple[tuple[Change, ...], ...]:
    """`rows` (one section, sorted by subject) split into consecutive same-subject runs."""
    groups: list[list[Change]] = []
    for row in rows:
        if groups and groups[-1][0].subject == row.subject:
            groups[-1].append(row)
        else:
            groups.append([row])
    return tuple(tuple(group) for group in groups)


def change_sections(diff: ListingDiff) -> tuple[ChangeSection, ...]:
    """The sections of `diff` that have a change, in the printed order, `unit` left out.

    Each `ChangeSection` holds its rows as groups of consecutive rows with the same `subject`
    (one note bullet each). A section with no row is absent; no change at all gives `()`.
    """
    by_section: dict[str, list[Change]] = {}
    for change in diff.changes:
        if change.section != "unit":
            by_section.setdefault(change.section, []).append(change)
    return tuple(
        ChangeSection(section=section, groups=_subject_groups(by_section[section]))
        for section in _SECTION_ORDER
        if section in by_section
    )
