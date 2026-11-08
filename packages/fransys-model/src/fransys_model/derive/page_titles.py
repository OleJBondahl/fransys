"""The title a drawing page prints, as candidate texts, longest first (PT1 to PT5, PAGES-TITLES).

`page_title_forms` is the one source: `drawing_text.page_title` returns its first text, and the
PDF frame prints the first one that fits its cell. The source of the entries, first match: the
texts of the page's own blocks (`page_title_groups`); the designations of the items it draws
(`page_designations`).
The forms shorten from the joined entries to "first to last" (one unit only) and "first and n
more" (layout-0268).
"""

from fransys_model.layout import (
    DrawingSet,
    Page,
    Shown,
    layout_of,
)
from fransys_model.layout.page_slices import page_members
from fransys_model.vocab import aspect_nodes, functions, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import AspectNode, Function, Unit

from .designation_label import terminal_of
from .document_subject import unit_label
from .drawing_text import page_title_groups
from .facts.house_settings import word
from .lookups import black_box_unit, unit_chain
from .tag_text import strip_tag_text, tag_text
from .unit_nodes import own_nodes_by_unit

_RANGE_ENTRIES = 2  # a range needs two entries


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
    """The designations the items on `page` print, in drawn order (G1, model-0348).

    A page is read from its `layout.membership` rows. No text record is ever the source of a title.
    """
    texts = [_function_text(model, function) for function in _member_functions(model, page)]
    return tuple(text for text in texts if text)


def _function_text(model: Model, function: Id[Function]) -> str:
    """A core symbol's entry: a strip terminal stands as its strip, any other as its tag."""
    if terminal_of(model, functions(model)[function].item) is not None:
        return strip_tag_text(model, function)
    return tag_text(model, function)


def _nested_unit(model: Model, set_unit: Id[Unit], node: Id[AspectNode]) -> Id[Unit] | None:
    """The unit directly in `set_unit` whose nodes hold `node`; `None` when `set_unit` holds it."""
    owners = [unit for unit, own in own_nodes_by_unit(model).items() if node in own and unit != set_unit and set_unit in unit_chain(model, unit)]
    if not owners:
        return None
    return black_box_unit(model, max(owners, key=lambda one: len(unit_chain(model, one))), set_unit)


def _block_entries(model: Model, page: Page) -> tuple[tuple[str, Id[Unit] | None], ...]:
    """The page's block texts, each with its unit; a nested unit's groups print its title.

    A group the set's unit owns, or any group of a set with no unit, has unit `None` (model-0256).
    """
    nodes = aspect_nodes(model)
    set_unit = layout_of(model, DrawingSet)[page.drawing_set].unit
    found: list[tuple[str, Id[Unit] | None]] = []
    for group in page_title_groups(model, page):
        nested = None if set_unit is None else _nested_unit(model, set_unit, group.group)
        if nested is None:
            found.append((nodes[group.group].description, None))
        else:
            found.append((unit_label(model, nested), nested))
    return tuple(found)


def _entries(model: Model, page: Page) -> tuple[tuple[str, Id[Unit] | None], ...]:
    """The title's entries, each text once, with its unit (`None`: the set's own, or no unit)."""
    if (blocks := _block_entries(model, page)) or layout_of(model, DrawingSet)[page.drawing_set].unit is not None:
        found = list(blocks)
    else:
        found = [(text, None) for text in page_designations(model, page)]
    once: dict[str, Id[Unit] | None] = {}
    for text, unit in found:
        once.setdefault(text, unit)
    return tuple(once.items())


def short_title(model: Model, entries: tuple[str, ...]) -> str | None:
    """`first to last` with their shared leading words printed once; `None` for one entry.

    "Relay 1" and "Relay 3" give "Relay 1 to 3"; with no shared word, or none left after it,
    "Supply to Pump 2". A first and last entry that are the same text have no short form.
    """
    if len(entries) < _RANGE_ENTRIES:
        return None
    first, last = entries[0], entries[-1]
    if first == last:
        return None
    head, tail = first.split(), last.split()
    shared = 0
    while shared < min(len(head), len(tail)) and head[shared] == tail[shared]:
        shared += 1
    if 0 < shared < min(len(head), len(tail)):
        last = " ".join(tail[shared:])
    return f"{first} {word(model, 'range_word')} {last}"


def _more_form(model: Model, entries: tuple[str, ...]) -> str:
    """The lead entry and how many more there are: "Pump and 4 more" (layout-0268)."""
    and_word, more_word = word(model, "and_word"), word(model, "more_word")
    return f"{entries[0]} {and_word} {len(entries) - 1} {more_word}"


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
    forms = [word(model, "list_join").join(entries)]
    candidates = [
        short_title(model, entries) if len({unit for _, unit in found}) == 1 else None,
        _more_form(model, entries) if len(entries) > 1 else None,
    ]
    for form in candidates:
        if form is not None and len(form) < len(forms[-1]):
            forms.append(form)
    return tuple(forms)


def page_title(model: Model, page: Page) -> str:
    """The page's title: the first, longest candidate text of `page_title_forms`."""
    return page_title_forms(model, page)[0]


__all__ = ["page_title", "page_title_forms", "short_title"]
