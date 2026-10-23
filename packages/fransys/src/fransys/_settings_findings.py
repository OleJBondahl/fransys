"""`SETTING_NEW_ENGINE_ONLY`: a grid or font key the old engine does not draw with (layout-0323).

The old engine keeps the built-in grid and font until MODEL-TEXT (SETTINGS amendment 5); the
new engine's drawings take the build's `Library`. One WARNING per key the consumer changed.
"""

from typing import TYPE_CHECKING, cast

from electrical_symbols import LIBRARY
from fransys_model.kernel import Finding, Severity

from ._codes import fix_text

if TYPE_CHECKING:
    from pathlib import Path

    from .settings import Settings

__all__ = ["new_engine_only_findings"]

CODE = "SETTING_NEW_ENGINE_ONLY"


def _keys(settings: Settings) -> list[tuple[str, str, str, str]]:
    """The (section, key, value text, built-in thing) of each grid or font key that differs."""
    found = []
    if settings.grid["module_mm"] != LIBRARY.grid.module_mm:
        found.append(("grid", "module_mm", str(settings.grid["module_mm"]), "grid"))
    if settings.font:
        if settings.font.get("name"):
            found.append(("font", "name", repr(settings.font["name"]), "font"))
        files = cast("tuple[Path, Path]", settings.font["files"])
        found.append(("font", "files", ", ".join(str(path) for path in files), "font"))
    return found


def new_engine_only_findings(settings: Settings) -> tuple[Finding, ...]:
    """One WARNING per grid or font key of `settings` that differs from the house library."""
    return tuple(
        Finding(
            code=CODE,
            severity=Severity.WARNING,
            subjects=(),
            message=(
                f"settings key {section} {key} = {value} applies to drawings from the new "
                f"engine; the old engine still draws with the built-in {built_in}"
            ),
            fix=fix_text(CODE),
        )
        for section, key, value, built_in in _keys(settings)
    )
