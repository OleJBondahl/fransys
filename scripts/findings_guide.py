"""Renders the tables of the guide's `findings-*.md` pages from the finding codes registry.

Run `uv run python scripts/findings_guide.py` after changing any package's finding codes registry.
Each page's prose stays as written; only its one table is rewritten, so the registry is the one
source of every code's row (BUILD-MESSAGES M8).
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import TYPE_CHECKING

from fransys import _codes  # noqa: PLC2701 -- the facade's merged registry is the one source

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import CodeInfo


class _Fields(dict[str, str]):
    """Maps each `{name}` field of a fix template to `<name>`."""

    def __missing__(self, key: str) -> str:
        return f"<{key}>"


HEADER = (
    "| Code | Severity | Stage | Who acts | Meaning | Fix |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
)


def page_names() -> tuple[str, ...]:
    """The guide page names the registry's codes point to, sorted."""
    return tuple(sorted({info.page for info in _codes.BY_CODE.values()}))


def _row(info: CodeInfo) -> str:
    severity = " or ".join(s.name for s in info.severities)
    cells = (info.code, severity, info.stage, info.who, info.cause, info.fix.format_map(_Fields()))
    return "| " + " | ".join(cells) + " |\n"


def render_table(infos: Iterable[CodeInfo]) -> str:
    """The page table: header, separator, then one row per code, sorted by code."""
    return HEADER + "".join(_row(info) for info in sorted(infos, key=lambda i: i.code))


def render_page(text: str, infos: Iterable[CodeInfo]) -> str:
    """`text` with its one table (its lines starting with `|`) replaced by the rendered table."""
    lines = text.splitlines(keepends=True)
    start = next(i for i, line in enumerate(lines) if line.startswith("|"))
    end = start
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    return "".join(lines[:start]) + render_table(infos) + "".join(lines[end:])


def expected_pages(guide_dir: Path) -> dict[Path, str]:
    """Each findings page's path under `guide_dir`, with the text it should hold."""
    pages: dict[Path, str] = {}
    for page in page_names():
        path = guide_dir / f"{page}.md"
        infos = [info for info in _codes.BY_CODE.values() if info.page == page]
        pages[path] = render_page(path.read_text(encoding="utf-8"), infos)
    return pages


def main() -> None:
    """Rewrite every findings page whose table is stale, and print the paths rewritten."""
    guide_dir = Path(str(importlib.resources.files("fransys").joinpath("guide")))
    for path, text in expected_pages(guide_dir).items():
        if path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            print(path)  # noqa: T201 -- this script's whole job is CLI output


if __name__ == "__main__":
    main()
