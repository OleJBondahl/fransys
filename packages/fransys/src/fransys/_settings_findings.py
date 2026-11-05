"""`SETTING_NEW_ENGINE_ONLY`: a font key the old engine does not draw with (layout-0323).

The old engine keeps the built-in font until MODEL-TEXT (SETTINGS amendment 5); the
new engine's drawings take the build's `Library`. One WARNING per key the consumer changed.
"""

from typing import TYPE_CHECKING, cast

lazy from fransys_model.kernel import Finding

from ._codes import finding

if TYPE_CHECKING:
    from pathlib import Path

    from .settings import Settings

__all__ = ["new_engine_only_findings"]

CODE = "SETTING_NEW_ENGINE_ONLY"


def _keys(settings: Settings) -> list[tuple[str, str, str, str]]:
    """The (section, key, value text, built-in thing) of each font key that differs."""
    found = []
    if settings.font:
        if settings.font.get("name"):
            found.append(("font", "name", repr(settings.font["name"]), "font"))
        files = cast("tuple[Path, Path]", settings.font["files"])
        found.append(("font", "files", ", ".join(str(path) for path in files), "font"))
    return found


def new_engine_only_findings(settings: Settings) -> tuple[Finding, ...]:
    """One WARNING per font key of `settings` that differs from the house library."""
    return tuple(
        finding(
            CODE,
            (),
            f"settings key {section} {key} = {value} applies to drawings from the new "
            f"engine; the old engine still draws with the built-in {built_in}",
        )
        for section, key, value, built_in in _keys(settings)
    )
