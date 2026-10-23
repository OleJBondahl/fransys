"""Readability row shapes (`fr.readability`).

Row shapes beside `rows.py` (model-0199); they import nothing from it.
"""

from typing import Any

from fransys_model.kernel import Id, value
from fransys_model.layout import Page
from fransys_model.vocab.core import Unit


@value
class DrawnPageReading:
    """What `fransys_el.readability` counts on one `Drawing`.

    `unit` is the unit of the drawing set the page belongs to, none at the top level. `symbols` and
    `markers` are the drawn symbols the page carries and, among them, the reference markers.
    `fill_percent` is the share of the content box the placed ink spans. `wire_crossings` counts
    wires of different ids crossing, `wire_bends` the turns of every wire and `wire_length_g` their
    length in G. `struck_labels` counts texts a wire runs through, `text_overlaps` pairs of texts
    whose boxes overlap.
    """

    page: Id[Page]
    unit: Id[Unit] | None
    symbols: int
    markers: int
    fill_percent: int
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
