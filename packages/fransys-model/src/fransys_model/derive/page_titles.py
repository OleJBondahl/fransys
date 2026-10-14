"""The title a drawing page prints, as candidate texts, longest first (PT1 to PT5, PAGES-TITLES).

`page_title_forms` is the one source: `drawing_text.page_title` returns its first text, and the
PDF frame prints the first one that fits its cell. The source of the entries, first match: the
texts of `layout.page_title` hints whose thing the page draws; the texts of the page's own
blocks (`page_title_groups`); the designations its item labels print, each once, in drawn order.
"""

lazy from collections.abc import Mapping

from fransys_model.layout import (
    DrawingSet,
    Label,
    LabelKind,
    Page,
    PageTitle,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab import aspect_nodes, functions, items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import AspectNode, Function, Item

from .designation import terminal_of
from .drawing_text import label_text, page_title_groups, strip_tag_text, unit_label
from .order import drawn_on_page

_JOIN = ", "


def _item_chains(model: Model, page: Page) -> list[frozenset[Id[Item]]]:
    """Per symbol of the page in drawn order, its item and every item above it."""
    records = items(model)
    chains = []
    for placement in drawn_on_page(model, SymbolPlacement, page):
        chain: list[Id[Item]] = []
        item: Id[Item] | None = functions(model)[placement.function].item
        while item is not None and item not in chain:
            chain.append(item)
            item = records[item].parent
        chains.append(frozenset(chain))
    return chains


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
    """The texts of the `PageTitle` hints whose thing the page draws: blocks, then drawn order."""
    hints = layout_of(model, PageTitle)
    if not hints:
        return ()
    blocks = {group.group: group.index for group in page.groups}
    placements = drawn_on_page(model, SymbolPlacement, page)
    drawn = [placement.function for placement in placements]
    chains = _item_chains(model, page)
    ranked = sorted(
        ((*rank, hint.key), hint.text)
        for hint in hints.values()
        if (rank := _drawn_rank(hint, blocks, drawn, chains)) is not None
    )
    return tuple(dict.fromkeys(text for _, text in ranked))


def _designation_entries(model: Model, page: Page) -> tuple[str, ...]:
    """The designations the page's item labels print, each once, in drawn order (G1)."""
    labels = drawn_on_page(model, Label, page)
    texts = (
        _entry_text(model, label)
        for label in labels
        if label.kind is LabelKind.TAG and label.slot != "outline_title"
    )
    return tuple(dict.fromkeys(text for text in texts if text))


def _entry_text(model: Model, label: Label) -> str:
    """The label's text; a strip terminal stands as its strip, "-X1" not "-X1:SIG:1" (PT2.3)."""
    function = label.function
    if function is not None and terminal_of(model, functions(model)[function].item) is not None:
        return strip_tag_text(model, function)
    return label_text(model, label)


def page_title_entries(model: Model, page: Page) -> tuple[str, ...]:
    """The title's entries (PT2): hint texts, else block texts, else printed designations.

    A page of a unit's own set takes no designations: with no hint and no block of its own it
    keeps the unit's title (PT5, model-0066).
    """
    if hinted := _hint_entries(model, page):
        return hinted
    nodes = aspect_nodes(model)
    blocks = tuple(nodes[group.group].description for group in page_title_groups(model, page))
    if blocks or layout_of(model, DrawingSet)[page.drawing_set].unit is not None:
        return blocks
    return _designation_entries(model, page)


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


def page_title_forms(model: Model, page: Page) -> tuple[str, ...]:
    """The candidate texts of `page`'s title, longest first: the joined entries, then a short form.

    A page with no entry keeps the unit's title in a unit's set, else the empty text.
    """
    entries = page_title_entries(model, page)
    if not entries:
        unit = layout_of(model, DrawingSet)[page.drawing_set].unit
        return ("" if unit is None else unit_label(model, unit),)
    joined = _JOIN.join(entries)
    short = short_title(entries)
    return (joined,) if short is None or len(short) >= len(joined) else (joined, short)


def page_title(model: Model, page: Page) -> str:
    """The page's title: the first, longest candidate text of `page_title_forms`."""
    return page_title_forms(model, page)[0]


__all__ = ["page_title", "page_title_entries", "page_title_forms", "short_title"]
