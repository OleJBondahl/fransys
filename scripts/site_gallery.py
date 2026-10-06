"""The examples gallery of the docs site (FS4, PM7): one page for the example folder, every export.

Every file under `out/` is linked: PDFs page by page, CSVs as tables, the rest as downloads.
Pictures come from `pypdfium2` (never pymupdf, AGPL). The build stops when a PDF's picture count
differs from its page count, so a rasterizer that drops a page cannot ship a gallery with a hole.
"""

from __future__ import annotations

import csv
import shutil
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pypdfium2

if TYPE_CHECKING:
    from pathlib import Path

PICTURE_WIDTH = 1600
KIND_ORDER = {".pdf": 0, ".csv": 1}


def rasterize(pdf: Path, dest: Path, width: int = PICTURE_WIDTH) -> list[Path]:
    """Write every page of `pdf` as `<stem>-pNN.png`, `width` pixels wide, in page order."""
    dest.mkdir(parents=True, exist_ok=True)
    document = pypdfium2.PdfDocument(pdf)
    written = []
    for number in range(len(document)):
        page = document[number]
        image = page.render(scale=width / page.get_size()[0]).to_pil()
        path = dest / f"{pdf.stem}-p{number + 1:02d}.png"
        image.save(path)
        written.append(path)
    return written


def check_picture_count(pdf: Path, pictures: list[Path]) -> None:
    """Fail the build when `pictures` on disk are not exactly one per page of `pdf`."""
    pages = len(pypdfium2.PdfDocument(pdf))
    on_disk = sorted(pictures[0].parent.glob(f"{pdf.stem}-p*.png")) if pictures else []
    if len(on_disk) != pages:
        msg = f"gallery: {pdf.name} has {pages} pages but {len(on_disk)} pictures"
        raise SystemExit(msg)


def export_groups(out: Path) -> dict[PurePosixPath, list[Path]]:
    """Every file under `out/`, sorted, grouped by its folder relative to `out/`."""
    groups: dict[PurePosixPath, list[Path]] = {}
    for path in sorted(p for p in out.rglob("*") if p.is_file()):
        groups.setdefault(PurePosixPath(path.parent.relative_to(out).as_posix()), []).append(path)
    return groups


def _pdf_lines(pdf: Path, rel: PurePosixPath, page_dir: Path) -> list[str]:
    pictures = rasterize(pdf, page_dir / "img" / rel.parent)
    check_picture_count(pdf, pictures)
    lines = [f"### {pdf.name}", "", f"[Download the PDF](files/{rel})", ""]
    for n, picture in enumerate(pictures, 1):
        target = PurePosixPath("img") / rel.parent / picture.name
        lines.append(f"[![{pdf.stem}, page {n}]({target})]({target})\n")
    return lines


def _table_row(cells: list[str]) -> str:
    return "| " + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in cells) + " |"


def _csv_lines(table: Path, rel: PurePosixPath) -> list[str]:
    with table.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    lines = [f"### {table.name}", "", f"[Download the CSV](files/{rel})", ""]
    if rows:
        lines += [_table_row(rows[0]), "|" + " --- |" * len(rows[0])]
        lines += [_table_row(row) for row in rows[1:]]
    return [*lines, ""]


def _file_lines(export: Path, rel: PurePosixPath, page_dir: Path) -> list[str]:
    if export.suffix == ".pdf":
        return _pdf_lines(export, rel, page_dir)
    if export.suffix == ".csv":
        return _csv_lines(export, rel)
    label = "Open the overview page" if export.name.endswith("-overview.html") else "Download"
    return [f"- {label}: [{export.name}](files/{rel})", ""]


def _section_lines(folder: PurePosixPath, exports: list[Path], page_dir: Path) -> list[str]:
    lines = [f"## {PurePosixPath('out') / folder}", ""]
    for export in sorted(exports, key=lambda e: (KIND_ORDER.get(e.suffix, 2), e.name)):
        rel = folder / export.name
        (page_dir / "files" / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(export, page_dir / "files" / rel)
        lines += _file_lines(export, rel, page_dir)
    return lines


def build_folder_page(folder: Path, src: Path, readme_snippet: str) -> str:
    """Stage the example folder's pictures, tables and downloads under `src`, return its page."""
    page_dir = src / "examples" / folder.name
    page_dir.mkdir(parents=True, exist_ok=True)
    parts = [f"# {folder.name}", "", f'--8<-- "{readme_snippet}"', ""]
    for group, exports in export_groups(folder / "out").items():
        parts += _section_lines(group, exports, page_dir)
    (page_dir / "index.md").write_text("\n".join(parts) + "\n", encoding="utf-8")
    return f"examples/{folder.name}/index.md"


def build_gallery(examples: Path, src: Path, snippets: Path) -> list[tuple[str, str]]:
    """Stage the gallery of the example folder `examples`; return `(name, page)` for the nav."""
    snippets.mkdir(parents=True, exist_ok=True)
    readme = (examples / "README.md").read_text(encoding="utf-8").splitlines(keepends=True)
    if readme and readme[0].startswith("# "):
        readme = readme[1:]
    (snippets / "examples-README.md").write_text("".join(readme).lstrip("\n"), encoding="utf-8")
    pages = [(examples.name, build_folder_page(examples, src, "snippets/examples-README.md"))]
    index = [
        "# Examples",
        "",
        "Whole designs from the examples repository, with their exports.",
        "",
    ]
    index += [f"- [{name}]({path.removeprefix('examples/')})" for name, path in pages]
    (src / "examples").mkdir(parents=True, exist_ok=True)
    (src / "examples" / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return pages
