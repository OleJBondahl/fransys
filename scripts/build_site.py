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

import findings_guide  # noqa: E402  its page list is the findings pages' one source
import fransys as fr  # noqa: E402  the home example's own page kinds
import fransys_pdf  # noqa: E402  the same
import lean_api  # noqa: E402  scripts/ goes on sys.path first, as the one home of the surface listing
import pypdfium2  # noqa: E402  the site group's pin; imported here only after sys.path is set
import site_gallery  # noqa: E402  sibling script, same reason
import site_markdown  # noqa: E402  the same

from fransys_model.derive.docs_site import OFFLINE_NOTE  # noqa: E402  the offline banner the site drops

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


ROW_CODE = re.compile(r"^\| ([A-Z][A-Z0-9_]+) \|", re.MULTILINE)


def anchor_rows(text: str) -> str:
    """Give each findings-table row the anchor `CodeInfo.see` names, its code in lower case (D6)."""
    return ROW_CODE.sub(lambda m: f'| <a id="{m[1].lower()}"></a>{m[1]} |', text)


def stage_guide() -> list[tuple[str, str]]:
    """Copy the guide pages without the offline banner; return `(nav title, page)` in nav order."""
    guide = Path(str(files("fransys").joinpath("guide")))
    (SRC / "guide").mkdir(parents=True)
    entries = []
    for name in (*guide_pages(), "AGENTS"):
        text = (guide / f"{name}.md").read_text(encoding="utf-8")
        text = text.replace(OFFLINE_NOTE + "\n\n", "")
        if name in findings_guide.page_names():
            text = anchor_rows(text)
        (SRC / "guide" / f"{name}.md").write_text(text, encoding="utf-8")
    for name in guide_pages():
        title = "Overview" if name == "index" else _title(guide / f"{name}.md")
        entries.append((title, f"guide/{name}.md"))
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


def plain(paragraph: str) -> str:
    """A paragraph with each `[text](link)` reduced to `text`; a relative link there is dead."""
    return re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", paragraph)


def llms_txt(sections: list[tuple[str, list[tuple[str, str]]]], site_url: str, version: str) -> str:
    """The llmstxt.org file: the version on line 1, a summary, then one list per section of pages.

    `site_url` is this version's root; each link is the page's Markdown copy (D2, D3).
    """
    first = sections[0][1][0][1]
    summary = opening_paragraph(SRC / first).split(". ")[0].rstrip(".") + "."
    lines = [f"# Fransys {version}", "", f"> {summary}", ""]
    lines += [
        f"Version {version}. Everything here is also in one file: {site_url}llms-full.txt.",
        "",
    ]
    for heading, entries in sections:
        lines += [f"## {heading}", ""]
        lines += [
            f"- [{title}]({site_url}{site_markdown.copy_path(page)}): "
            f"{plain(opening_paragraph(SRC / page))}"
            for title, page in entries
        ]
        lines.append("")
    return "\n".join(lines)


def versioned_url() -> str:
    """This build's site root: the config's `site_url` plus `<X.Y.Z>/`."""
    config = (WEBSITE / "mkdocs.yml").read_text(encoding="utf-8")
    site_url = re.search(r"^site_url:\s*(\S+)", config, re.MULTILINE)
    if site_url is None:
        msg = "site_url not found in website/mkdocs.yml"
        raise SystemExit(msg)
    return f"{site_url.group(1).rstrip('/')}/{fr.__version__}/"


CONTRACTS = (
    ("Part file contract", "contracts/part-file.md"),
    ("Part file connectors", "contracts/part-file-connectors.md"),
)


def stage_llms(guide: list[tuple[str, str]], api: list[tuple[str, str]]) -> None:
    """Write `llms.txt` and `llms-full.txt` into the staged pages (copied to the site root)."""
    url = versioned_url()
    sections = [("Guide", guide), ("Part files", list(CONTRACTS)), ("API", api)]
    (SRC / "llms.txt").write_text(llms_txt(sections, url, fr.__version__), encoding="utf-8")
    pages = [page for _, entries in sections for _, page in entries]
    head = (
        f"# Fransys {fr.__version__}\n\n"
        "> The whole guide, the part-file contracts and the API pages in one file.\n"
    )
    full = site_markdown.llms_full(SRC, STATE, pages, url, head)
    (SRC / "llms-full.txt").write_text(full, encoding="utf-8")


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
        ("Part files", list(CONTRACTS)),
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
    (SRC / "contracts").mkdir()
    for name in ("part-file.md", "part-file-connectors.md"):
        shutil.copy2(ROOT / "docs" / "contracts" / name, SRC / "contracts" / name)
    gallery = site_gallery.build_gallery(examples, SRC, SNIPPETS)
    stage_roadmap()
    api = stage_api()
    stage_llms(guide, api)
    sections = nav_sections(guide, gallery, api)
    config = (WEBSITE / "mkdocs.yml").read_text(encoding="utf-8")
    config = re.sub(r"^site_url:.*$", f"site_url: {versioned_url()}", config, flags=re.MULTILINE)
    config = re.sub(r"^site_dir:.*$", "site_dir: site-build", config, flags=re.MULTILINE)
    config += f'copyright: "Fransys {fr.__version__} documentation"\n'
    nav = "\n".join(_nav_lines(sections))
    (STATE / "mkdocs.yml").write_text(config + nav + "\n", encoding="utf-8")


def site_root() -> str:
    """The site's root URL, above every version: the config's `site_url`."""
    return versioned_url().removesuffix(f"{fr.__version__}/")


ROOT_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Fransys documentation</title>
<meta http-equiv="refresh" content="0; url=latest/">
<link rel="canonical" href="{root}latest/">
</head>
<body>
<p><a href="latest/">Fransys documentation, latest release ({version})</a></p>
</body>
</html>
"""

ROOT_LLMS = """# Fransys

> Fransys is a Python toolkit for electrical cabinet and harness design.

The documentation is versioned. Latest release: {version}.

- Latest: {root}latest/llms.txt (the whole guide in one file: {root}latest/llms-full.txt)
- A given release: {root}<X.Y.Z>/llms.txt, for example {root}{version}/llms.txt
- Markdown of any page: its URL plus index.md, under the same version path
- Pick the version from the installed `fransys.__version__`
"""


def lay_out(built: Path) -> None:
    """Fill `OUT`: the build at `<X.Y.Z>/` and `latest/`, a root redirect and a root llms.txt.

    A version that is not `X.Y.Z` fails here, so no path is named after a dev build.
    """
    version = fr.__version__
    if re.fullmatch(r"\d+\.\d+\.\d+", version) is None:
        msg = f"fransys.__version__ {version!r} is not X.Y.Z: the site has no path for it"
        raise SystemExit(msg)
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    for name in (version, "latest"):
        shutil.copytree(built, OUT / name)
    fields = {"root": site_root(), "version": version}
    (OUT / "index.html").write_text(ROOT_PAGE.format(**fields), encoding="utf-8")
    (OUT / "llms.txt").write_text(ROOT_LLMS.format(**fields), encoding="utf-8")


def build() -> None:
    """Build with Zensical strict, add the Markdown copies, check every link, fill `OUT`."""
    built = STATE / "site-build"
    shutil.rmtree(built, ignore_errors=True)
    subprocess.run(
        [sys.executable, "-m", "zensical", "build", "--strict", "-f", "mkdocs.yml"],
        cwd=STATE,
        check=True,
    )
    site_markdown.write_copies(SRC, STATE, built)
    checked = site_markdown.check_links(built, versioned_url())
    sys.stdout.write(f"link check: {checked} links, 0 dead\n")
    lay_out(built)


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
