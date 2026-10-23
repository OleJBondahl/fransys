"""The title a drawing page prints, as candidate texts, longest first (PT1 to PT5, PAGES-TITLES).

`page_title_forms` is the one source: `drawing_text.page_title` returns its first text, and the
PDF frame prints the first one that fits its cell. The source of the entries, first match: the
texts of `layout.page_title` hints whose thing the page draws; the texts of the page's own
blocks (`page_title_groups`); the designations of the items it draws (`page_designations`).
The forms shorten from the joined entries to "first to last" (one unit only) and "first and n
more" (layout-0268).
"""

lazy from collections.abc import Mapping

from fransys_model.layout import (
    DrawingSet,
    Page,
    PageTitle,
    Shown,
    layout_of,
)
from fransys_model.layout.page_slices import page_members
from fransys_model.vocab import aspect_nodes, functions, items, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import AspectNode, Function, Item, Unit

from .designation_label import terminal_of
from .drawing_text import page_title_groups, strip_tag_text, unit_label
from .lookups import black_box_unit, unit_chain
from .tag_text import tag_text
from .unit_nodes import own_nodes_by_unit

_JOIN = ", "


def _drawn_functions(model: Model, page: Page) -> tuple[Id[Function], ...]:
    """The functions `page` draws in drawn order: its membership rows."""
    return _member_functions(model, page)


def _drawn_items(model: Model, page: Page) -> tuple[Id[Item], ...]:
    """The items `page` draws: its membership item and function rows."""
    found = [row.item for row in page_members(model, page) if row.item is not None]
    found += [functions(model)[function].item for function in _member_functions(model, page)]
    return tuple(found)


def _item_chains(model: Model, page: Page) -> list[frozenset[Id[Item]]]:
    """Per symbol of the page in drawn order, its item and every item above it."""
    records = items(model)
    chains = []
    for function in _drawn_functions(model, page):
        chain: list[Id[Item]] = []
        item: Id[Item] | None = functions(model)[function].item
        while item is not None and item not in chain:
            chain.append(item)
            item = records[item].parent
        chains.append(frozenset(chain))
    return chains


def _draws_unit(model: Model, page: Page, unit: Id[Unit]) -> bool:
    """Whether `page`, of another set, draws `unit`: a symbol or a connector box of its items."""
    if layout_of(model, DrawingSet)[page.drawing_set].unit == unit:
        return False
    owners = (items(model)[item].unit for item in _drawn_items(model, page))
    return any(owner is not None and unit in unit_chain(model, owner) for owner in owners)


def _drawn_rank(
    hint: PageTitle,
    blocks: Mapping[Id[AspectNode], int],
    drawn: list[Id[Function]],
    chains: list[frozenset[Id[Item]]],
) -> tuple[int, int] | None:
    """Where the page draws `hint`'s thing, as a sort key; `None` when it does not."""
    if hint.block is not None:
        return (0, blocks[hint.block]) if hint.block in blocks else None
    if hint.function is not None:
        return (1, drawn.index(hint.function)) if hint.function in drawn else None
    at = next((i for i, chain in enumerate(chains) if hint.item in chain), None)
    return None if at is None else (1, at)


def _hint_entries(model: Model, page: Page) -> tuple[str, ...]:
    """The texts of the `PageTitle` hints whose thing the page draws: blocks, drawn order, units."""
    hints = layout_of(model, PageTitle)
    if not hints:
        return ()
    blocks = {group.group: group.index for group in page.groups}
    drawn = list(_drawn_functions(model, page))
    chains = _item_chains(model, page)
    ranked = [
        ((*rank, hint.key), hint.text)
        for hint in hints.values()
        if hint.unit is None and (rank := _drawn_rank(hint, blocks, drawn, chains)) is not None
    ]
    ranked += [
        ((2, 0, hint.key), hint.text)
        for hint in hints.values()
        if hint.unit is not None and _draws_unit(model, page, hint.unit)
    ]
    return tuple(dict.fromkeys(text for _, text in sorted(ranked)))


def _member_functions(model: Model, page: Page) -> tuple[Id[Function], ...]:
    """The functions `page` draws, in reading order: its function rows and drawn port rows."""
    owner = {port: one.function for port, one in ports(model).items()}
    found: list[Id[Function]] = []
    for row in page_members(model, page):
        if row.function is not None:
            found.append(row.function)
        elif row.port is not None and row.shown is Shown.DRAWN:
            found.append(owner[row.port])
    return tuple(found)


def page_designations(model: Model, page: Page) -> tuple[str, ...]:
    """The designations the items on `page` print, each once, in drawn order (G1, model-0348).

    A page is read from its `layout.membership` rows. No text record is ever the source of a title.
    """
    texts = [_function_text(model, function) for function in _member_functions(model, page)]
    return tuple(dict.fromkeys(text for text in texts if text))


def _function_text(model: Model, function: Id[Function]) -> str:
    """A core symbol's entry: a strip terminal stands as its strip, any other as its tag."""
    if terminal_of(model, functions(model)[function].item) is not None:
        return strip_tag_text(model, function)
    return tag_text(model, function)


def _nested_unit(model: Model, set_unit: Id[Unit], node: Id[AspectNode]) -> Id[Unit] | None:
    """The unit directly in `set_unit` whose nodes hold `node`; `None` when `set_unit` holds it."""
    owners = [
        unit
        for unit, own in own_nodes_by_unit(model).items()
        if node in own and unit != set_unit and set_unit in unit_chain(model, unit)
    ]
    if not owners:
        return None
    return black_box_unit(model, max(owners, key=lambda one: len(unit_chain(model, one))), set_unit)


def _block_entries(model: Model, page: Page) -> tuple[tuple[str, Id[Unit] | None], ...]:
    """The page's block texts, each with its unit; a nested unit's groups print its title once.

    A group the set's unit owns, or any group of a set with no unit, has unit `None` (model-0256).
    """
    nodes = aspect_nodes(model)
    set_unit = layout_of(model, DrawingSet)[page.drawing_set].unit
    found: list[tuple[str, Id[Unit] | None]] = []
    for group in page_title_groups(model, page):
        nested = None if set_unit is None else _nested_unit(model, set_unit, group.group)
        if nested is None:
            found.append((nodes[group.group].description, None))
        elif (label := unit_label(model, nested)) not in (text for text, _ in found):
            found.append((label, nested))
    return tuple(found)


def _entries(model: Model, page: Page) -> tuple[tuple[str, Id[Unit] | None], ...]:
    """The title's entries, each with its unit (`None`: the set's own, or no unit)."""
    if hinted := _hint_entries(model, page):
        return tuple((text, None) for text in hinted)
    blocks = _block_entries(model, page)
    if blocks or layout_of(model, DrawingSet)[page.drawing_set].unit is not None:
        return blocks
    return tuple((text, None) for text in page_designations(model, page))


def page_title_entries(model: Model, page: Page) -> tuple[str, ...]:
    """The title's entries (PT2): hint texts, else block texts, else printed designations.

    A page of a unit's own set takes no designations: with no hint and no block of its own it
    keeps the unit's title (PT5, model-0066).
    """
    return tuple(text for text, _ in _entries(model, page))


def short_title(entries: tuple[str, ...]) -> str | None:
    """`first to last` with their shared leading words printed once; `None` for one entry.

    "Relay 1" and "Relay 3" give "Relay 1 to 3"; with no shared word, or none left after it,
    "Supply to Pump 2". A first and last entry that are the same text have no short form.
    """
    if len(entries) < 2:  # noqa: PLR2004 -- a range needs two entries
        return None
    first, last = entries[0], entries[-1]
    if first == last:
        return None
    head, tail = first.split(), last.split()
    shared = 0
    while shared < min(len(head), len(tail)) and head[shared] == tail[shared]:
        shared += 1
    if 0 < shared < min(len(head), len(tail)):
        return f"{first} to {' '.join(tail[shared:])}"
    return f"{first} to {last}"


def _more_form(entries: tuple[str, ...]) -> str:
    """The lead entry and how many more there are: "Pump and 4 more" (layout-0268)."""
    return f"{entries[0]} and {len(entries) - 1} more"


def page_title_forms(model: Model, page: Page) -> tuple[str, ...]:
    """The candidate texts of `page`'s title, each shorter than the one before.

    The joined entries; then "first to last", only when every entry names one unit; then
    the lead entry and "and n more". The frame prints the first that fits.
    A page with no entry keeps the unit's title in a unit's set, else the empty text.
    """
    found = _entries(model, page)
    if not found:
        unit = layout_of(model, DrawingSet)[page.drawing_set].unit
        return ("" if unit is None else unit_label(model, unit),)
    entries = tuple(text for text, _ in found)
    forms = [_JOIN.join(entries)]
    candidates = [
        short_title(entries) if len({unit for _, unit in found}) == 1 else None,
        _more_form(entries) if len(entries) > 1 else None,
    ]
    for form in candidates:
        if form is not None and len(form) < len(forms[-1]):
            forms.append(form)
    return tuple(forms)


def page_title(model: Model, page: Page) -> str:
    """The page's title: the first, longest candidate text of `page_title_forms`."""
    return page_title_forms(model, page)[0]


__all__ = ["page_title", "page_title_entries", "page_title_forms", "short_title"]
