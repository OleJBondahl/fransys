"""`python -m fransys help KEY` for a public name: its signature, docstring and guide page."""

import annotationlib
import importlib.resources
import inspect
import re
from dataclasses import dataclass

import fransys
from fransys_model.derive.docs_site import version_url

_HANDLES = {"detail": "Detail", "layout": "Layout"}


@dataclass(frozen=True)
class Resolved:
    """One public name found: its display key, signature line, docstring and guide page."""

    key: str
    signature: str
    doc: str
    page: str | None
    heading: str | None


def _member(owner: object, name: str) -> object | None:
    return getattr(owner, name, None) if name in dir(owner) else None


def _target(key: str) -> tuple[str, object | None]:
    """The display key and the object a bare, `fr.` or `d.` key names."""
    bare = key.removeprefix("fr.")
    if not bare.startswith("d."):
        return f"fr.{bare}", getattr(fransys, bare, None) if bare in fransys.__all__ else None
    head, _, rest = bare.removeprefix("d.").partition(".")
    if head in _HANDLES:
        return bare, _member(getattr(fransys, _HANDLES[head]), rest)
    return bare, _member(fransys.Design, head) if not rest else None


def _signature(obj: object) -> str:
    if not callable(obj):
        return f"constant of type {type(obj).__name__}"
    target = obj.__init__ if inspect.isclass(obj) else obj
    sig = inspect.signature(target, annotation_format=annotationlib.Format.STRING)
    params = [q for q in sig.parameters.values() if q.name != "self"]
    return str(sig.replace(parameters=params))


def _guide_pages() -> list[tuple[str, list[str]]]:
    """The guide pages in `index.md` link order, `index.md` first; the first naming a thing wins."""
    guide = importlib.resources.files("fransys").joinpath("guide")
    index = guide.joinpath("index.md").read_text(encoding="utf-8")
    present = {p.name for p in guide.iterdir()}
    linked = dict.fromkeys(re.findall(r"[\w.-]+\.md", index))
    names = ["index.md", *(n for n in linked if n in present)]
    return [(n, guide.joinpath(n).read_text(encoding="utf-8").splitlines()) for n in names]


def _heading_page(shown: str, pages: list[tuple[str, list[str]]]) -> tuple[str, str] | None:
    for name, lines in pages:
        for line in lines:
            if line.startswith("## ") and line.strip("# ") == f"`{shown}`":
                return name, line
    return None


def _mention_page(shown: str, pages: list[tuple[str, list[str]]]) -> tuple[str, str] | None:
    bare = shown.removeprefix("fr.")
    for name, lines in pages:
        heading = ""
        for line in lines:
            heading = line if line.startswith("#") else heading
            if f"`{shown}`" in line or f"`{bare}`" in line:
                return name, heading
    return None


def _guide_page(shown: str) -> tuple[str, str] | None:
    pages = _guide_pages()
    return _heading_page(shown, pages) or _mention_page(shown, pages)


def resolve(key: str) -> Resolved | None:
    """The public name `key` (`write`, `fr.write`, `d.device`, `d.detail.wire`), or None."""
    shown, obj = _target(key)
    if obj is None:
        return None
    page = _guide_page(shown)
    return Resolved(shown, _signature(obj), inspect.getdoc(obj) or "", *(page or (None, None)))


def names_text(found: Resolved) -> str:
    """The printed form of one found name: signature, docstring and where the guide covers it."""
    lines = [
        f"{found.key}{found.signature}"
        if found.signature.startswith("(")
        else f"{found.key}: {found.signature}",
        "",
    ]
    lines += [found.doc, ""] if found.doc else []
    if found.page:
        lines.append(f"guide: {found.page}: {found.heading}")
        lines.append(f"site: {version_url(fransys.__version__)}guide/{found.page}")
    return "\n".join(lines)
