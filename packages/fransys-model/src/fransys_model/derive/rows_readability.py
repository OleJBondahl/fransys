"""Readability row shapes (`fr.readability`).

Row shapes beside `rows.py` (model-0199); they import nothing from it.
"""

from typing import Any

from fransys_model.kernel import Id, value
from fransys_model.layout import Page


@value
class DrawnPageReading:
    """What `fransys_el.readability` counts on one `Drawing`.

    `symbols` and `markers` are the cells and references the page carries. `wire_crossings` counts
    wires of different ids crossing, `wire_bends` the turns of every wire and `wire_length_g` their
    length in G. `struck_labels` counts texts a wire runs through, `text_overlaps` pairs of texts
    whose boxes overlap.
    """

    page: Id[Page]
    symbols: int
    markers: int
    wire_crossings: int
    wire_bends: int
    wire_length_g: int
    struck_labels: int
    text_overlaps: int


@value
class DrawnReading:
    """What `fransys_el.readability` returns: one `DrawnPageReading` for each page, in order."""

    pages: tuple[DrawnPageReading, ...]


@value
class OffDocumentReference:
    """A printed reference to a page of another document that its text does not name.

    `subject` is the link marker, `page` the page it stands on, `target` the page it names.
    """

    subject: Id[Any]
    page: Id[Page]
    target: Id[Page]
