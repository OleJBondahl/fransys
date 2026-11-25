"""The cover/notes Markdown subset: parsing, escaping and Typst emission.

Every text run reaches Typst as a string literal (`text("...")`), never as markup: a `#`,
`*`, `_`, `@`, `<`, `$` or backtick an engineer types is printed as typed, whether or not the
line also matches one of the six supported constructs. `parse` never raises for text; a
construct outside the six supported ones becomes its own `Unsupported` element carrying the
line number and the verbatim line, in reading order among the supported elements, so `source`
can still print it (as its own paragraph) and `check` can still report it (P6, P11).
"""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ._typst import literal

if TYPE_CHECKING:
    from collections.abc import Callable

_HEADING = re.compile(r"^(#{1,3}) (.*)$")
_DEEP_HEADING = re.compile(r"^(#{4,}) ")
_BULLET = re.compile(r"^- (.*)$")
_NUMBERED = re.compile(r"^\d+\. (.*)$")
_CODE_FENCE = re.compile(r"^```")
_BLOCK_QUOTE = re.compile(r"^>")
_INDENTED_LIST = re.compile(r"^[ \t]+(?:[-*+] |\d+\. )")
_TABLE_ROW = re.compile(r"^\s*\|")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[[^\]]*\]\([^)]*\)")
_INLINE_CODE = re.compile(r"`[^`]+`")
_RAW_HTML = re.compile(r"<[a-zA-Z/][^>]*>")
# Emphasis opens only before a non-space and closes only after one (CommonMark's flanking
# rule, reduced to this subset): `a * b * c` stays literal, `a *b* c` opens italic.
_INLINE_RUN = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*|\*(?=\S)(.+?)(?<=\S)\*")


def _deep_heading(line: str) -> str | None:
    match = _DEEP_HEADING.match(line)
    return None if match is None else f"heading level {len(match.group(1))}"


# Tried in this order; the first match names the line's construct. A code fence or an
# indentation signal is checked before a heading depth, so a fenced or indented line is never
# misreported as a plain deep heading.
_UNSUPPORTED_CHECKS: tuple[Callable[[str], str | None], ...] = (
    lambda line: "code fence" if _CODE_FENCE.match(line) else None,
    lambda line: "block quote" if _BLOCK_QUOTE.match(line) else None,
    lambda line: "indented list" if _INDENTED_LIST.match(line) else None,
    _deep_heading,
    lambda line: "table" if _TABLE_ROW.match(line) else None,
    lambda line: "image" if _IMAGE.search(line) else None,
    lambda line: "link" if _LINK.search(line) else None,
    lambda line: "inline code" if _INLINE_CODE.search(line) else None,
    lambda line: "raw HTML" if _RAW_HTML.search(line) else None,
)


@dataclass(frozen=True, slots=True)
class Run:
    """One span of inline text: `kind` is `"plain"`, `"bold"` or `"italic"`."""

    kind: str
    text: str


@dataclass(frozen=True, slots=True)
class Heading:
    """A `#`/`##`/`###` line. `line` is 1-based, within the text `parse` was given."""

    line: int
    level: int
    runs: tuple[Run, ...]


@dataclass(frozen=True, slots=True)
class Paragraph:
    """Lines joined by a space, ended by a blank line or another construct."""

    line: int
    runs: tuple[Run, ...]


@dataclass(frozen=True, slots=True)
class BulletList:
    """Consecutive `- ` lines; no nesting."""

    line: int
    items: tuple[tuple[Run, ...], ...]


@dataclass(frozen=True, slots=True)
class NumberedList:
    """Consecutive `<number>. ` lines; no nesting."""

    line: int
    items: tuple[tuple[Run, ...], ...]


@dataclass(frozen=True, slots=True)
class Unsupported:
    """A line outside the six supported constructs: its line number, name and verbatim text."""

    line: int
    construct: str
    text: str


type Element = Heading | Paragraph | BulletList | NumberedList | Unsupported


def _runs(text: str) -> tuple[Run, ...]:
    """`text` split into plain/bold/italic runs; an unmatched `*` stays part of a plain run."""
    runs: list[Run] = []
    pos = 0
    for match in _INLINE_RUN.finditer(text):
        if match.start() > pos:
            runs.append(Run("plain", text[pos : match.start()]))
        bold = match.group(1)
        runs.append(Run("bold", bold) if bold is not None else Run("italic", match.group(2)))
        pos = match.end()
    if pos < len(text) or not runs:
        runs.append(Run("plain", text[pos:]))
    return tuple(runs)


def _unsupported_construct(line: str) -> str | None:
    """The name of the unsupported construct `line` triggers, or `None` when it is plain text."""
    return next(filter(None, (check(line) for check in _UNSUPPORTED_CHECKS)), None)


class _Group:
    """The consecutive lines or items of one kind that `parse` is accumulating, and the element they close into."""

    def __init__(self, elements: list[Element], close: Callable[[int, list[Any]], Element]) -> None:
        self._elements = elements
        self._close = close
        self._items: list[Any] = []
        self._line = 0

    def add(self, index: int, item: object) -> None:
        if not self._items:
            self._line = index
        self._items.append(item)

    def flush(self) -> None:
        if self._items:
            self._elements.append(self._close(self._line, self._items))
            self._items = []


class _Blocks:
    """The paragraph, bullet and numbered-list groups `parse` is accumulating, in order."""

    def __init__(self) -> None:
        self.elements: list[Element] = []
        self.paragraph = _Group(self.elements, lambda line, items: Paragraph(line, _runs(" ".join(items))))
        self.bullets = _Group(self.elements, lambda line, items: BulletList(line, tuple(items)))
        self.numbers = _Group(self.elements, lambda line, items: NumberedList(line, tuple(items)))

    def flush_all(self) -> None:
        self.paragraph.flush()
        self.bullets.flush()
        self.numbers.flush()


def _fold_block(blocks: _Blocks, index: int, line: str) -> bool:
    """Fold an unsupported line or a heading into `blocks`; False when `line` is neither."""
    construct = _unsupported_construct(line)
    if construct is not None:
        blocks.flush_all()
        blocks.elements.append(Unsupported(index, construct, line))
        return True
    heading = _HEADING.match(line)
    if heading is not None:
        blocks.flush_all()
        blocks.elements.append(Heading(index, len(heading.group(1)), _runs(heading.group(2))))
        return True
    return False


def _fold_item(blocks: _Blocks, index: int, line: str) -> bool:
    """Fold a bullet or numbered item into `blocks`; False when `line` is neither."""
    bullet = _BULLET.match(line)
    if bullet is not None:
        blocks.paragraph.flush()
        blocks.numbers.flush()
        blocks.bullets.add(index, _runs(bullet.group(1)))
        return True
    numbered = _NUMBERED.match(line)
    if numbered is not None:
        blocks.paragraph.flush()
        blocks.bullets.flush()
        blocks.numbers.add(index, _runs(numbered.group(1)))
        return True
    return False


def _handle_line(blocks: _Blocks, index: int, line: str) -> None:
    """Classify one line and fold it into `blocks`: a flush, a new element, or accumulation."""
    if line.strip() == "":
        blocks.flush_all()
    elif not (_fold_block(blocks, index, line) or _fold_item(blocks, index, line)):
        blocks.bullets.flush()
        blocks.numbers.flush()
        blocks.paragraph.add(index, line)


def parse(text: str) -> tuple[Element, ...]:
    """`text`'s Markdown subset as elements, in reading order. Never raises."""
    blocks = _Blocks()
    for index, line in enumerate(text.splitlines(), start=1):
        _handle_line(blocks, index, line)
    blocks.flush_all()
    return tuple(blocks.elements)


def unsupported(elements: tuple[Element, ...]) -> tuple[Unsupported, ...]:
    """Every `Unsupported` element of `elements`, in reading order."""
    return tuple(element for element in elements if isinstance(element, Unsupported))


def _run_typst(run: Run) -> str:
    body = f"text({literal(run.text)})"
    if run.kind == "bold":
        return f"strong({body})"
    if run.kind == "italic":
        return f"emph({body})"
    return body


def _runs_typst(runs: tuple[Run, ...]) -> str:
    return " + ".join(_run_typst(run) for run in runs)


def _element_typst(element: Element) -> str:
    if isinstance(element, Heading):
        return f"#heading(level: {element.level}, {_runs_typst(element.runs)})"
    if isinstance(element, Paragraph):
        return f"#par({_runs_typst(element.runs)})"
    if isinstance(element, BulletList):
        items = ", ".join(_runs_typst(item) for item in element.items)
        return f"#list({items})"
    if isinstance(element, NumberedList):
        items = ", ".join(_runs_typst(item) for item in element.items)
        return f"#enum({items})"
    return f"#par({_run_typst(Run('plain', element.text))})"


def to_typst(elements: tuple[Element, ...]) -> str:
    """`elements` as Typst source statements, one `#...` line per element."""
    return "\n".join(_element_typst(element) for element in elements)
