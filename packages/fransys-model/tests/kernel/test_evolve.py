"""Tests: `kernel.evolve`."""

from typing import Any

import pytest
from freeze_probes import (
    draft_of,
    make_facet,
    make_holder,
    make_owner,
    owner_id,
)

from fransys_model.kernel import (
    Model,
    Origin,
    RefError,
    evolve,
    freeze,
)

_BASE = Origin(file="base.py", line=1, note="")
_CALL = Origin(file="pass.py", line=9, note="numbering")


def _model(*records: Any) -> Model:
    return freeze(draft_of(_BASE, *records))


def _base() -> Model:
    """Owners 1, 2 and 3, a holder of owner 1, and a facet of owner 1."""
    return _model(
        make_owner("1"), make_owner("2"), make_owner("3"), make_holder("5"), make_facet("7", "1")
    )


def _aliased() -> Model:
    """Owners 1 and 2 and holder 5, with owner 8 retired in favour of owner 1."""
    draft = draft_of(_BASE, make_owner("1"), make_owner("2"), make_holder("5"))
    draft.alias(owner_id("8"), owner_id("1"))
    return freeze(draft)


def test_evolve_treats_a_retired_id_used_as_a_reference_as_any_dangling_id() -> None:
    """No rewriting: a put record that still says the old id points at nothing."""
    with pytest.raises(RefError, match="names no record") as excinfo:
        evolve(_aliased(), put=(make_holder("6", owner=owner_id("8")),), origin=_CALL)
    assert excinfo.value.target == owner_id("8")
