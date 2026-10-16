"""The one reader of a reference's kind (layout-0292 b)."""

from __future__ import annotations

from .values import Ref, RefKind


def kind_of(ref: Ref) -> RefKind:
    """A class pattern, so no `.kind` attribute read is spread about the stages."""
    match ref:
        case Ref(kind=kind):
            return kind
