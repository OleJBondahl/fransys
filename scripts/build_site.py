"""`just site EXAMPLES_DIR` (decision 0105, experimental): stage the docs site and build it strict.

Pages are staged into `.fransys/site-src/` and built into `.fransys/site/`; both are
intermediates and nothing is copied into a tracked file. The nav follows `GUIDE_PAGES` in
`tests/test_guide_examples.py`, with `AGENTS.md` last. Run through `uv run --group site`.
"""

from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
from importlib.resources import files
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fransys as fr  # noqa: E402  the home example's own page kinds
import fransys_pdf  # noqa: E402  the same
import lean_api  # noqa: E402  scripts/ goes on sys.path first, as the one home of the surface listing
import pypdfium2  # noqa: E402  the site group's pin; imported here only after sys.path is set
import site_gallery  # noqa: E402  sibling script, same reason

STATE = ROOT / ".fransys"
SRC = STATE / "site-src"
OUT = STATE / "site"
SNIPPETS = STATE / "snippets"
WEBSITE = ROOT / "website"
API_MODULES = (("fransys", "fransys.md"), ("fransys_model.derive", "derive.md"))


def guide_pages() -> tuple[str, ...]:
    """`GUIDE_PAGES`, read from the test module's source so the nav has one list."""
    tree = ast.parse((ROOT / "tests" / "test_guide_examples.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "GUIDE_PAGES" for t in node.targets
        ):
            return tuple(ast.literal_eval(node.value))
    msg = "GUIDE_PAGES not found in tests/test_guide_examples.py"
    raise SystemExit(msg)


def _title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def stage_guide() -> list[tuple[str, str]]:
    """Copy the guide's pages unchanged; return `(nav title, page path)` in nav order."""
    guide = Path(str(files("fransys").joinpath("guide")))
    (SRC / "guide").mkdir(parents=True)
    entries = []
    for name in guide_pages():
        shutil.copy2(guide / f"{name}.md", SRC / "guide" / f"{name}.md")
        title = "Overview" if name == "index" else _title(guide / f"{name}.md")
        entries.append((title, f"guide/{name}.md"))
    shutil.copy2(guide / "AGENTS.md", SRC / "guide" / "AGENTS.md")
    entries.append(("For coding agents", "guide/AGENTS.md"))
    return entries


def opening_paragraph(path: Path) -> str:
    """The first paragraph after a page's `# title`, as one line."""
    lines = path.read_text(encoding="utf-8").splitlines()
    body = lines[next(i for i, line in enumerate(lines) if line.startswith("# ")) + 1 :]
    paragraph: list[str] = []
    for line in body:
        if line.strip():
            paragraph.append(line.strip())
        elif paragraph:
            break
    return " ".join(paragraph)


def llms_txt(entries: list[tuple[str, str]], site_url: str) -> str:
    """The llmstxt.org file: title, a one-line summary, one line per page of `entries`."""
    summary = opening_paragraph(SRC / entries[0][1]).split(". ")[0].rstrip(".") + "."
    lines = ["# Fransys", "", f"> {summary}", "", "## Guide", ""]
    for title, page in entries:
        url = f"{site_url}{page.removesuffix('.md').removesuffix('index')}"
        url += "" if url.endswith("/") else "/"
        lines.append(f"- [{title}]({url}): {opening_paragraph(SRC / page)}")
    return "\n".join(lines) + "\n"


def stage_llms(guide: list[tuple[str, str]]) -> None:
    """Write `llms.txt` at the site root from the guide pages already staged."""
    config = (WEBSITE / "mkdocs.yml").read_text(encoding="utf-8")
    site_url = re.search(r"^site_url:\s*(\S+)", config, re.MULTILINE)
    if site_url is None:
        msg = "site_url not found in website/mkdocs.yml"
        raise SystemExit(msg)
    (SRC / "llms.txt").write_text(
        llms_txt(guide, site_url.group(1).rstrip("/") + "/"), encoding="utf-8"
    )


def stage_api() -> list[tuple[str, str]]:
    """One generated page per consumer surface (`lean_api --md`), plus a short index."""
    (SRC / "api").mkdir()
    entries = [("Overview", "api/index.md")]
    index = ["# API reference", "", "Every name each public surface exports.", ""]
    for module, filename in API_MODULES:
        (SRC / "api" / filename).write_text(lean_api.api_md(module), encoding="utf-8")
        entries.append((module, f"api/{filename}"))
        index.append(f"- [`{module}`]({filename})")
    (SRC / "api" / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return entries


def stage_home() -> None:
    """Stage the home page, its example, and the picture of the example's first schematic page."""
    shutil.copy2(WEBSITE / "index.md", SRC / "index.md")
    shutil.copy2(WEBSITE / "extra.css", SRC / "extra.css")
    shutil.copytree(WEBSITE / "overrides", STATE / "overrides", dirs_exist_ok=True)
    SNIPPETS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WEBSITE / "example.py", SNIPPETS / "example.py")
    kinds = [
        k.value
        for k in fransys_pdf.page_kinds(fr.DocumentPreset.CABINET_SCHEMATIC)
        if k.value != "notes"
    ]
    with tempfile.TemporaryDirectory() as work:
        subprocess.run([sys.executable, str(WEBSITE / "example.py")], cwd=work, check=True)  # noqa: S603  our own script, no outside input
        (pdf,) = Path(work, "out").glob("*.pdf")
        document = pypdfium2.PdfDocument(pdf)
        page = document[kinds.index("schematic")]
        image = page.render(scale=site_gallery.PICTURE_WIDTH / page.get_size()[0]).to_pil()
    shutil.copytree(WEBSITE / "assets", SRC / "assets")
    image.save(SRC / "assets" / "home.png")


def stage_roadmap() -> None:
    """Stage the roadmap page, which sits after Examples in the nav."""
    shutil.copy2(WEBSITE / "roadmap.md", SRC / "roadmap.md")


def nav_sections(
    guide: list[tuple[str, str]], gallery: list[tuple[str, str]], api: list[tuple[str, str]]
) -> list[tuple[str, list[tuple[str, str]] | str]]:
    """The nav entries after Home, in order; a plain path is a page, Roadmap, after Examples."""
    return [
        ("Guide", guide),
        ("Part files", [("Part file contract", "contracts/part-file.md")]),
        ("Examples", [("Overview", "examples/index.md"), *gallery]),
        ("Roadmap", "roadmap.md"),
        ("API", api),
    ]


def _nav_lines(sections: list[tuple[str, list[tuple[str, str]] | str]]) -> list[str]:
    lines = ["", "nav:", "  - Home: index.md"]
    for title, entries in sections:
        if isinstance(entries, str):
            lines.append(f"  - {json.dumps(title)}: {entries}")
            continue
        lines.append(f"  - {json.dumps(title)}:")
        lines += [f"    - {json.dumps(label)}: {path}" for label, path in entries]
    return lines


def stage(examples: Path) -> None:
    """Rebuild `site-src/` and the generated `mkdocs.yml` from scratch."""
    for folder in (SRC, OUT, SNIPPETS):
        shutil.rmtree(folder, ignore_errors=True)
    SRC.mkdir(parents=True)
    stage_home()
    guide = stage_guide()
    stage_llms(guide)
    (SRC / "contracts").mkdir()
    shutil.copy2(ROOT / "docs" / "contracts" / "part-file.md", SRC / "contracts" / "part-file.md")
    gallery = site_gallery.build_gallery(examples, SRC, SNIPPETS)
    stage_roadmap()
    sections = nav_sections(guide, gallery, stage_api())
    config = (WEBSITE / "mkdocs.yml").read_text(encoding="utf-8")
    nav = "\n".join(_nav_lines(sections))
    (STATE / "mkdocs.yml").write_text(config + nav + "\n", encoding="utf-8")


def build() -> None:
    """Run Zensical strict from `.fransys/`, the project root of the staged config."""
    subprocess.run(
        [sys.executable, "-m", "zensical", "build", "--strict", "-f", "mkdocs.yml"],
        cwd=STATE,
        check=True,
    )


def main() -> None:
    """CLI entry point: `build_site.py EXAMPLES_DIR`."""
    if len(sys.argv) != 2:  # noqa: PLR2004  script name and the one argument
        sys.stderr.write("usage: build_site.py EXAMPLES_DIR\n")
        sys.exit(2)
    stage(Path(sys.argv[1]).resolve())
    build()
    sys.stdout.write(f"site built: {OUT}\n")


if __name__ == "__main__":
    main()
