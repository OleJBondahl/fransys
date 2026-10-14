"""`LayoutOptions`: a text kind with no row fails when the options are built (seam 1)."""

import pytest
from fransys_el import TEXTS

from fransys_layout import LayoutOptions, TextKind
from fransys_layout.geometry import LayoutError


def test_options_with_every_kind_build() -> None:
    assert LayoutOptions(texts=TEXTS).texts is TEXTS


def test_a_kind_with_no_row_fails_when_the_options_are_built() -> None:
    """The caller's table must cover every text kind the core places."""
    without_tag = frozendict({k: v for k, v in TEXTS.items() if k != TextKind.TAG.value})
    with pytest.raises(LayoutError, match="no row for tag"):
        LayoutOptions(texts=without_tag)
