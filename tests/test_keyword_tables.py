"""Keyword tables (API-CLARITY C3, A3): each public call has a table that matches its signature.

The guide pages `keywords-*.md` hold one table per call: keyword, default, effect, example.
The keywords equal the signature's named parameters, each default cell equals the signature's
default and no effect cell is empty. `d.layout.profile` and `d.layout.sheet` keep their tables
in `layout-numbers.md`.
"""

import enum
import inspect
import re
from pathlib import Path

import fransys as fr
from test_tier_words import namespaced, tiered

GUIDE = Path(fr.__file__).parent / "guide"
PAGES = ("keywords-design.md", "keywords-handles.md", "keywords-output.md")
EXEMPT = {"d.layout.profile", "d.layout.sheet"}
NAMED = (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
_HEAD = re.compile(r"^## `([^`]+)`$")
_LINK = re.compile(r"^\[(`[^`]+`)\]\(([\w.-]+\.md)#([\w-]+)\)$")
# Rows with no guide heading that explains the keyword (KEYWORD-LINKS): the set only shrinks.
NO_HOME = frozenset(
    {
        ("d.device", "tag"),
        ("d.device", "name"),
        ("d.device", "mounted_on"),
        ("d.device", "description"),
        ("d.device", "position"),
        ("d.device", "installed"),
        ("d.terminal_strip", "tag"),
        ("d.terminal_strip", "part"),
        ("d.terminal_strip", "name"),
        ("d.terminal_strip", "description"),
        ("d.cable", "tag"),
        ("d.cable", "part"),
        ("d.cable", "length_m"),
        ("d.cable", "name"),
        ("d.cable", "external"),
        ("d.add", "definition"),
        ("d.add", "tag"),
        ("d.add", "name"),
        ("d.ac_supply", "name"),
        ("d.dc_supply", "name"),
        ("d.harness", "name"),
        ("d.harness", "external"),
        ("d.rack", "tag"),
        ("d.rack", "name"),
        ("d.rack", "external"),
        ("d.project", "revision"),
        ("d.project", "version"),
        ("d.revision", "checked"),
        ("d.revision", "approved"),
        ("d.rating", "part"),
        ("d.rating", "function"),
        ("d.operating", "part"),
        ("d.operating", "function"),
        ("Fn.plc", "priority"),
        ("Fn.scale", "unit"),
        ("Cable.spare", "at"),
        ("d.layout.break_before", "group"),
        ("d.layout.draw_in", "function"),
        ("d.layout.draw_in", "group"),
        ("d.layout.symbol", "target"),
        ("d.layout.symbol", "symbol"),
        ("d.layout.symbol", "port_map"),
        ("fr.unit", "name"),
        ("fr.unit", "interface_version"),
        ("fr.unit", "title"),
        ("fr.unit", "number"),
        ("fr.readability", "result"),
        ("fr.check", "result"),
        ("fr.report", "result"),
        ("fr.write", "result"),
        ("fr.export_names", "result"),
        ("fr.release", "result"),
        ("fr.diff", "result"),
        ("fr.diff", "baselines"),
        ("fr.diff", "unit"),
        ("fr.diff", "against"),
        ("fr.verify", "result"),
        ("fr.rebaseline", "result"),
        ("fr.rebaseline", "baselines"),
        ("fr.rebaseline", "unit"),
    }
)


def calls() -> dict[str, object]:
    found = dict(tiered())
    found |= {k: v for k, v in namespaced().items() if not k.startswith("fr.derive.")}
    return {k: v for k, v in found.items() if k not in EXEMPT}


def named(call: object) -> list[inspect.Parameter]:
    params = inspect.signature(call).parameters.values()  # ty: ignore[invalid-argument-type] # call is a function
    return [p for p in params if p.kind in NAMED and p.name not in ("self", "cls")]


def default_cell(p: inspect.Parameter) -> str:
    v = p.default
    if v is inspect.Parameter.empty:
        return "required"
    if v is Ellipsis:
        return "`...`"
    if isinstance(v, enum.Enum):
        return (
            f"`fr.{v.name}`" if getattr(fr, v.name, None) is v else f"`{type(v).__name__}.{v.name}`"
        )
    return f"`{v!r}`"


def sections() -> dict[str, list[list[str]]]:
    """Each call heading to the cells of its table rows, header and rule excluded."""
    found: dict[str, list[list[str]]] = {}
    for page in PAGES:
        current = None
        for line in (GUIDE / page).read_text().splitlines():
            head = _HEAD.match(line)
            if head:
                current = head.group(1)
                assert current not in found, f"two sections for {current}"
                found[current] = []
            elif current and line.startswith("| ") and not line.startswith("| keyword"):
                cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
                cells[0] = _LINK.sub(r"\1", cells[0])
                found[current].append(cells)
    return found


def slug(heading: str) -> str:
    """Python-Markdown's default toc id of a heading."""
    plain = re.sub(r"[^\w\s-]", "", heading.strip()).strip().lower()
    return re.sub(r"[-\s]+", "-", plain)


def anchors(page: str) -> set[str]:
    lines = (GUIDE / page).read_text().splitlines()
    return {slug(m.group(1)) for line in lines if (m := re.match(r"#{1,6} (.+)$", line))}


def first_cells() -> list[tuple[str, str]]:
    """Each (call, raw first cell) of every table row."""
    out = []
    for page in PAGES:
        current = None
        for line in (GUIDE / page).read_text().splitlines():
            head = _HEAD.match(line)
            current = head.group(1) if head else current
            if current and line.startswith("| ") and not line.startswith("| keyword"):
                out.append((current, line.strip().strip("|").split(" | ")[0].strip()))
    return out


def link_problems() -> list[str]:
    bad = []
    for call, cell in first_cells():
        link = _LINK.match(cell)
        key = (call, cell.strip("`"))
        if not link:
            if key not in NO_HOME:
                bad.append(f"{call} {cell}: no link and not in NO_HOME")
        elif (call, link[1].strip("`")) in NO_HOME:
            bad.append(f"{call} {cell}: linked but still in NO_HOME")
        elif not (GUIDE / link[2]).is_file():
            bad.append(f"{call} {cell}: page {link[2]} does not exist")
        elif link[3] not in anchors(link[2]):
            bad.append(f"{call} {cell}: {link[2]} has no anchor #{link[3]}")
    return bad


def test_every_public_call_has_a_section_and_no_other_section_exists():
    assert set(sections()) == set(calls()), set(sections()) ^ set(calls())


def test_table_keywords_equal_the_signatures_named_parameters():
    table = sections()
    bad = {
        k: ([r[0] for r in table[k]], [f"`{p.name}`" for p in named(v)])
        for k, v in calls().items()
        if [r[0] for r in table[k]] != [f"`{p.name}`" for p in named(v)]
    }
    assert not bad, f"table keywords differ from the signature: {bad}"


def test_table_defaults_equal_the_signatures_defaults():
    table = sections()
    bad = {}
    for k, v in calls().items():
        want = [default_cell(p) for p in named(v)]
        got = [r[1] for r in table[k]]
        if got != want:
            bad[k] = (got, want)
    assert not bad, f"default cells differ from the signature: {bad}"


def test_every_row_has_an_effect_and_an_example():
    empty = [(k, r[0]) for k, rows in sections().items() for r in rows if len(r) != 4 or not all(r)]
    assert not empty, f"rows with an empty or missing cell: {empty}"


def test_the_collector_sees_calls():
    assert {"fr.build", "d.device", "d.layout.symbol", "Cable.core"} <= set(calls())
    assert "d.layout.profile" not in calls()


def test_every_keyword_row_links_to_an_existing_page_and_anchor():
    assert not link_problems(), link_problems()
