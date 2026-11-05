"""The consumer's `[font]`, `[lines]`, `[dash]` and the build's `Library` (ST3-ST5)."""

from pathlib import Path
from typing import TYPE_CHECKING, cast

from electrical_symbols import LIBRARY, Library, SymdefError

from ._settings_merge import SettingsError, Table, known

if TYPE_CHECKING:
    from collections.abc import Mapping
    from enum import Enum

    from .settings import Settings

__all__ = ["build_library", "font_dirs", "library_of", "merged_font", "weight_name"]

_FONT_KEYS = ("name", "files")
_FILES_HINT = "`files = [regular, bold]`: two TrueType paths, relative to the settings file"


def _face(base: Path | None, text: object, which: str, where: str) -> Path:
    """The path `text` of the `which` face, relative to the settings file; it must exist."""
    if not isinstance(text, str):
        msg = f'{where} [font] "files" must be {_FILES_HINT}; the {which} path is {text!r}'
        raise SettingsError(msg)
    path = Path(text) if base is None else base / text
    if not path.is_file():
        msg = f'{where} [font] the {which} font file {path} does not exist; fix the path in "files"'
        raise SettingsError(msg)
    return path


def merged_font(given: Table, where: str, base: Path | None) -> dict[str, object]:
    """The `[font]` table: empty (the house font) or `name` and the two `files` paths."""
    own = given
    if not own:
        return {}
    if "heights" in own:
        msg = f"{where} [font.heights] is removed: text heights are the library's fixed heights; delete the table"
        raise SettingsError(msg)
    for key in own:
        if key not in _FONT_KEYS:
            msg = f'{where} [font] "{key}" is not a setting; known: {known(_FONT_KEYS)}'
            raise SettingsError(msg)
    files = own.get("files")
    if not isinstance(files, list) or len(files) != len(("regular", "bold")):
        msg = f"{where} [font] needs {_FILES_HINT}, got {files!r}"
        raise SettingsError(msg)
    regular, bold = (_face(base, text, which, where) for text, which in zip(files, ("regular", "bold"), strict=True))
    return {"name": str(own.get("name", "")), "files": (regular, bold)}


def weight_name(weight: Enum) -> str:
    """The settings key of a symdef line weight: `[lines]` and the drawing record spell it so."""
    return weight.name.lower()


def build_library(
    font: Mapping[str, object],
    tables: Mapping[str, Mapping[str, object]],
    where: str,
) -> Library:
    """The build's `Library`: `LIBRARY` with the merged font, lines and dashes.

    `tables` holds the merged `lines` and `dash` whole; symdef replaces each table
    with them. Raises `SettingsError` when symdef refuses a value or a text leaves its body.
    """
    files = cast("tuple[Path, Path]", font.get("files"))
    pair = None if not font else (files[0].read_bytes(), files[1].read_bytes())
    weights = {weight_name(weight): weight for weight in LIBRARY.lines}
    lines = cast("Mapping[str, float]", tables["lines"])
    dash = cast("Mapping[str, list[float]]", tables["dash"])
    try:
        return LIBRARY.with_settings(
            font=pair,
            lines={weights[name]: float(mm) for name, mm in lines.items()},
            dash={name: tuple(float(mm) for mm in run) for name, run in dash.items()},
        )
    except SymdefError as error:
        msg = f"{where} [font]: {error}"
        raise SettingsError(msg) from error


def library_of(settings: Settings) -> Library:
    """The build's `Library` for `settings`, made once per build."""
    tables = {
        "lines": settings.table("lines"),
        "dash": settings.table("dash"),
    }
    return build_library(settings.font, tables, "the settings")


def font_dirs(font: Mapping[str, object]) -> tuple[Path, ...]:
    """The folders Typst reads fonts from: the consumer's two faces' folders, else none."""
    files = cast("tuple[Path, Path]", font.get("files", ()))
    return tuple(dict.fromkeys(path.parents[0] for path in files))
