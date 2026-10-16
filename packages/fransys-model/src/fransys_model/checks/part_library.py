"""Validator: one part library name carries one version (design/vocabulary.md 6, 7)."""

from collections import defaultdict
from typing import TYPE_CHECKING, Final

from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.tables import part_libraries

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.vocab.templates import PartLibrary

PART_LIBRARY_VERSION_CONFLICT: Final[str] = "PART_LIBRARY_VERSION_CONFLICT"


def check_part_library(model: Model) -> tuple[Finding, ...]:
    """Check no library name is recorded with two different versions.

    `PART_LIBRARY_VERSION_CONFLICT` (`ERROR`): two `PartLibrary` of one `name`, two `version`s.
    A hand-keyed pair gets here: `freeze()` re-derives no id. Sorted by `(code, subjects, message)`.
    """
    by_name: defaultdict[str, list[PartLibrary]] = defaultdict(list)
    for library in part_libraries(model).values():
        by_name[library.name].append(library)
    found = [
        Finding(
            code=PART_LIBRARY_VERSION_CONFLICT,
            severity=Severity.ERROR,
            subjects=tuple(library.id for library in libraries),
            message=(
                f"part library {name} is recorded with versions "
                + ", ".join(sorted({library.version for library in libraries}))
            ),
        )
        for name, libraries in by_name.items()
        if len({library.version for library in libraries}) > 1
    ]
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
