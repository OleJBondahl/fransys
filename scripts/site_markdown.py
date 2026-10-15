"""Markdown copies of the staged pages, `llms-full.txt`, and the link check (DOCS-FOR-AGENTS D2-D5).

Each staged `*.md` page is published again as Markdown at its page URL plus `index.md`, from the
same source file. Links in the copy are rewritten so they resolve on the site: a relative `.md`
link becomes the target page's `index.md` copy. A link that leaves the staged pages (a repository
path, a missing page) fails the build and names the link.
"""

from __future__ import annotations

import posixpath
import re
from typing import TYPE_CHECKING
from urllib.parse import unquote, urldefrag, urlparse

if TYPE_CHECKING:
    from pathlib import Path

INLINE_LINK = re.compile(r"(\]\()([^)\s]+)((?:\s+\"[^\"]*\")?\))")
SNIPPET = re.compile(r'^--8<--\s+"([^":]+)(?::([\w-]+))?"\s*$')
SNIPPET_COMMENT = re.compile(r"^<!--\s*--8<--\s*\[(?:start|end):[\w-]+\]\s*-->\s*$")
ANCHOR = re.compile(r'<a id="[\w-]+"></a>')
HREF = re.compile(r"""(?:href|src)=["']([^"']+)["']""")
ID = re.compile(r"""\bid=["']([^"']+)["']""")


class SiteLinkError(SystemExit):
    """The staged pages or the built site hold a link that does not resolve on the site."""


def page_dir(page: str) -> str:
    """The URL folder of a staged page path: `guide/foo.md` is `guide/foo`, `index.md` is ``."""
    stem = page.removesuffix(".md")
    return "" if stem == "index" else stem.removesuffix("/index")


def copy_path(page: str) -> str:
    """Where the Markdown copy of staged page `page` is published, relative to the site root."""
    folder = page_dir(page)
    return f"{folder}/index.md" if folder else "index.md"


def _expand_snippets(text: str, base: Path, page: str) -> str:
    out: list[str] = []
    for line in text.splitlines():
        if SNIPPET_COMMENT.match(line):
            continue
        found = SNIPPET.match(line)
        if found is None:
            out.append(line)
            continue
        source = base / found.group(1)
        if not source.is_file():
            msg = f"{page}: snippet {found.group(1)} does not exist"
            raise SiteLinkError(msg)
        out.extend(_section(source.read_text(encoding="utf-8"), found.group(2)))
    return "\n".join(out) + "\n"


def _section(text: str, name: str | None) -> list[str]:
    lines = text.splitlines()
    if name is None:
        return lines
    start = next((i for i, ln in enumerate(lines) if f"[start:{name}]" in ln), None)
    end = next((i for i, ln in enumerate(lines) if f"[end:{name}]" in ln), None)
    if start is None or end is None:
        msg = f"snippet section {name} not found"
        raise SiteLinkError(msg)
    return lines[start + 1 : end]


def _target(link: str, page: str, pages: set[str], files: set[str]) -> str | None:
    """The site file the link of staged `page` names, or None for an outside link."""
    path, _ = urldefrag(link)
    if not path or urlparse(link).scheme or link.startswith(("//", "#", "mailto:")):
        return None
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(page), unquote(path)))
    if resolved.startswith("..") or resolved not in files:
        msg = f"{page}: link {link!r} resolves to {resolved!r}, not a page or file of the site"
        raise SiteLinkError(msg)
    return copy_path(resolved) if resolved in pages else resolved


def rewrite_links(
    text: str, page: str, pages: set[str], files: set[str], site_url: str = ""
) -> str:
    """`text` with each local link made to resolve on the site (absolute with `site_url`)."""
    here = page_dir(page)
    out: list[str] = []
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        out.append(
            line if fenced else INLINE_LINK.sub(_swap(page, here, pages, files, site_url), line)
        )
    return "\n".join(out) + "\n"


def _swap(page: str, here: str, pages: set[str], files: set[str], site_url: str):  # noqa: ANN202  an re.sub callback
    def swap(found: re.Match[str]) -> str:
        link = found.group(2)
        dest = _target(link, page, pages, files)
        if dest is None:
            return found.group(0)
        fragment = urldefrag(link)[1]
        new = site_url + dest if site_url else posixpath.relpath(dest, here or ".")
        return f"{found.group(1)}{new}{'#' + fragment if fragment else ''}{found.group(3)}"

    return swap


def staged_files(src: Path) -> set[str]:
    """Every file under `src`, as POSIX paths relative to it."""
    return {p.relative_to(src).as_posix() for p in src.rglob("*") if p.is_file()}


def markdown_copy(src: Path, base: Path, page: str, site_url: str = "") -> str:
    """The published Markdown of staged `page`: snippets expanded, links rewritten."""
    files = staged_files(src)
    pages = {f for f in files if f.endswith(".md")}
    text = ANCHOR.sub("", _expand_snippets((src / page).read_text(encoding="utf-8"), base, page))
    return rewrite_links(text, page, pages, files, site_url)


def write_copies(src: Path, base: Path, out: Path) -> list[str]:
    """Write every staged page's Markdown copy under `out`; return the copies' site paths."""
    written = []
    for page in sorted(f for f in staged_files(src) if f.endswith(".md")):
        target = out / copy_path(page)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown_copy(src, base, page), encoding="utf-8")
        written.append(copy_path(page))
    return written


def llms_full(src: Path, base: Path, pages: list[str], site_url: str, head: str) -> str:
    """One file: `head`, then each page of `pages` as its Markdown copy with absolute links."""
    parts = [head.rstrip("\n") + "\n"]
    for page in pages:
        body = markdown_copy(src, base, page, site_url)
        parts.append(f"<!-- source: {site_url}{copy_path(page)} -->\n\n{body}")
    return "\n---\n\n".join(parts)


def _links_of(path: Path, site_url: str) -> list[str]:
    text = path.read_text(encoding="utf-8")
    found = (
        HREF.findall(text) if path.suffix == ".html" else [m[1] for m in INLINE_LINK.findall(text)]
    )
    return [site_url_local(link, site_url) for link in found]


def site_url_local(link: str, site_url: str) -> str:
    """An absolute link into this version's site as a site-relative one; others unchanged."""
    return "/" + link.removeprefix(site_url) if site_url and link.startswith(site_url) else link


def check_links(root: Path, site_url: str) -> int:
    """Fail on any link in the built site `root` that does not resolve; return the links checked.

    A target ending `.md` must be a published `index.md` copy; a target outside `root`, a missing
    file or a missing `#fragment` of an HTML page fails, naming the page and the link.
    """
    base_path = urlparse(site_url).path if site_url else ""
    problems: list[str] = []
    count = 0
    for page in sorted(p for p in root.rglob("*") if p.suffix in {".html", ".md", ".txt"}):
        for link in _links_of(page, site_url):
            count += 1
            problem = _problem(root, page, link, base_path)
            if problem:
                problems.append(f"{page.relative_to(root)}: {link} {problem}")
    if problems:
        shown = "\n  ".join(problems[:40])
        msg = f"site link check: {len(problems)} dead or non-site links\n  {shown}"
        raise SiteLinkError(msg)
    return count


def _problem(root: Path, page: Path, link: str, base_path: str) -> str | None:
    path, fragment = urldefrag(link)
    if not path or urlparse(link).scheme or link.startswith(("//", "mailto:")):
        return None
    path = unquote(path)
    if path.startswith("/"):
        target = root / path.removeprefix(base_path).lstrip("/")
    else:
        target = root / posixpath.normpath(
            posixpath.join(page.parent.relative_to(root).as_posix(), path)
        )
    if not target.resolve().is_relative_to(root.resolve()):
        return "leaves the site"
    if path.endswith(".md") and not path.endswith("index.md"):
        return "is a source .md path, not a published copy"
    if target.is_dir():
        target /= "index.html"
    if not target.is_file():
        return "does not exist"
    if fragment and target.suffix == ".html" and fragment not in ids_of(target):
        return f"has no anchor #{fragment}"
    return None


_IDS: dict[Path, set[str]] = {}


def ids_of(page: Path) -> set[str]:
    """The `id` attributes of an HTML page, cached per path."""
    if page not in _IDS:
        _IDS[page] = set(ID.findall(page.read_text(encoding="utf-8")))
    return _IDS[page]
