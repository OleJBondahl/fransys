"""`fr.settings`: our defaults from the TOML files, a consumer's file and `paper=` on top (ST2)."""

import dataclasses
import tomllib
from functools import cache
from importlib import resources
from pathlib import Path
from typing import cast
lazy from collections.abc import Mapping

from fransys_model.vocab import PageKind

from ._settings_library import build_library, merged_font, merged_grid
from ._settings_merge import SettingsError, Table, merged_tables, paper_by_kind

__all__ = ["Settings", "SettingsError", "settings"]

# Stock until SETTINGS-C (ST7): the block diagram is on A2 unless Python names another paper.
_HOUSE_BY_KIND: Mapping[PageKind, str] = {PageKind.BLOCK_DIAGRAM: "A2"}


def _frozen(value: object) -> object:
    """`value` with every dict a `frozendict` and every list a tuple, all the way down."""
    if isinstance(value, dict):
        return frozendict({key: _frozen(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_frozen(item) for item in value)
    return value


def _frozen_table(table: Table) -> frozendict[str, object]:
    """A settings table, frozen."""
    return frozendict({key: _frozen(item) for key, item in table.items()})


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Settings:
    """Every setting of one build: our defaults, then the consumer's file, key by key.

    `paper` holds `default` (a format name) and `formats` (name to the sheet's numbers);
    `paper_by_kind` names a format for one `PageKind`. `pdf`, `look` and `layout` hold the other
    tables. `grid` holds `module_mm`; `font` is empty for our font, else `name` and the two font
    `files` paths. A key in `pdf`, `look` or `layout` raises only when it is unknown or of another
    type than ours. `table(name)` gives any merged table of our TOML files. Make one with
    `fr.settings()`, pass it to `fr.build`.
    """

    paper: frozendict[str, object]
    paper_by_kind: frozendict[PageKind, str]
    grid: frozendict[str, object]
    font: frozendict[str, object]
    pdf: frozendict[str, object]
    look: frozendict[str, object]
    layout: frozendict[str, object]
    _merged: frozendict[str, frozendict[str, object]] = dataclasses.field(
        init=False, repr=False, compare=False
    )

    def table(self, name: str) -> frozendict[str, object]:
        """The merged table `name` of our TOML files (`pdf`, `look`, `layout`, or a later one)."""
        if name not in self._merged:
            msg = f"[{name}] is not a settings table; known: {', '.join(self._merged)}"
            raise SettingsError(msg)
        return self._merged[name]


def _package_toml(package: str, name: str) -> Table:
    """The TOML file `name` shipped inside `package`."""
    return tomllib.loads((resources.files(package) / name).read_text(encoding="utf-8"))


def settings(
    path: str | Path | None = None, *, paper: Mapping[PageKind, str] | None = None
) -> Settings:
    """Core: our defaults with a consumer's TOML file on top, key by key, and `paper=` per kind.

    `path` is a settings file naming only what differs from our defaults; `None` gives our
    defaults. `paper` maps a `PageKind` to a paper format's name, such as
    `{fr.PageKind.BLOCK_DIAGRAM: "A2"}`; it is the one spelling of a paper per drawing type, and
    a per-kind key in the TOML file raises. Only the formats `A3` and `A2` exist today.
    Does not build, write a file or touch the environment; it reads the TOML files only.

    Raises:
        SettingsError: the file is missing, has an unknown key, a value of another type than
            ours, a key outside the overridable tables, or `paper` names an unknown format. The
            message names the file, the key and the keys known there.
    """
    if path is None and not paper:
        return _house()
    return _merge(path, paper)


@cache
def _house() -> Settings:
    """Our defaults, built once (a frozen value)."""
    return _merge(None, None)


def _merge(path: str | Path | None, paper: Mapping[PageKind, str] | None) -> Settings:
    """The settings of `path` (or none) and `paper`."""
    layout = _package_toml("fransys_layout", "layout.toml")
    ours: Table = {"pdf": {}, **_package_toml("fransys", "settings.toml"), **layout}
    file = None if path is None else Path(path)
    consumer = {} if file is None else _read(file)
    where = "our defaults" if file is None else str(file)
    tables = merged_tables(ours, consumer, where)
    grid, font = _library_tables(consumer, file, where)
    build_library(grid, font, _build_tables(tables), where)
    kinds = paper_by_kind(tables["paper"], {**_HOUSE_BY_KIND, **dict(paper or {})})
    built = Settings(
        paper=_frozen_table(tables["paper"]),
        paper_by_kind=frozendict(kinds),
        grid=_frozen_table(grid),
        font=_frozen_table(font),
        pdf=_frozen_table(tables["pdf"]),
        look=_frozen_table(tables["look"]),
        layout=_frozen_table(tables["layout"]),
    )
    merged = frozendict({n: _frozen_table(t) for n, t in tables.items() if n != "paper"})
    object.__setattr__(built, "_merged", merged)  # init=False: never a constructor keyword
    return built


def _library_tables(
    consumer: Table, path: Path | None, where: str
) -> tuple[dict[str, object], dict[str, object]]:
    """The merged `[grid]` and `[font]`; symdef's checks run here, so an error names the file."""
    grid = merged_grid(cast("Table", consumer.get("grid", {})), where)
    given = cast("Table", consumer.get("font", {}))
    font = merged_font(given, where, None if path is None else path.parents[0])
    return grid, font


def _build_tables(tables: Mapping[str, Table]) -> dict[str, Table]:
    """The merged `lines`, `dash` and `heights` tables `build_library` hands to symdef whole."""
    heights = tables["font"]["heights"]
    return {"lines": tables["lines"], "dash": tables["dash"], "heights": cast("Table", heights)}


def _read(file: Path) -> Table:
    """The consumer's file as plain tables."""
    try:
        return tomllib.loads(file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        msg = f"settings file {file} does not exist: pass the path of your TOML file or none"
        raise SettingsError(msg) from None
    except tomllib.TOMLDecodeError as error:
        msg = f"settings file {file} is not valid TOML: {error}"
        raise SettingsError(msg) from None
