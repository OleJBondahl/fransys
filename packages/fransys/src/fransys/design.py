"""`design`: the staleness check in front of the typed parts module's surface (EA-PARTS)."""

lazy from types import ModuleType

from fransys_author import AuthorError
from fransys_author.surface import Design

from fransys.parts_module import library_digest
from fransys.pipeline import parts


def _check_fresh(module: ModuleType) -> None:
    if library_digest(*module.SOURCES) != module.LIBRARY_DIGEST:
        name = getattr(module, "__name__", repr(module))
        message = (
            f"parts module {name} is stale for its sources {list(module.SOURCES)}: "
            "regenerate with python -m fransys parts-module"
        )
        raise AuthorError(message)


def design(*libraries: str | ModuleType, place: str | None = None) -> Design:
    """Start a `Design` from part-library names or generated parts modules, each checked fresh.

    `place` names the first location, as a bare tag.

    Does not write files, build, or create devices.
    """
    sources: list[str] = []
    for item in libraries:
        if isinstance(item, str):
            sources.append(item)
            continue
        _check_fresh(item)
        sources.extend(item.SOURCES)
    return Design(parts(*sources), place=place)
