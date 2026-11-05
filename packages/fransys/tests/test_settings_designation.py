"""The first number an automatic designation takes is 1 (SO-C part C)."""

from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
import pytest

from fransys_model.vocab import facets_of
from fransys_model.vocab.facets.assigned_designation import AssignedDesignationFacet

pytestmark = pytest.mark.wp("facade")


class _Open(NamedTuple):
    """The cabinet hands nothing back."""


def _numbered(path: Path | None) -> fr.BuildResult:
    """A cabinet of two floating relays, built under `path`."""

    @fr.unit(
        "demo-cab",
        revision=1,
        interface_version=1,
        date="2026-02-01",
        text="first",
        by="AB",
    )
    def cab(u: Any) -> _Open:
        for name in ("a", "b"):
            u.device(None, "DEMO-RLY-2CO-24", name=name)
        return _Open()

    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.add(cab, "U1")
    return fr.build(d, settings=fr.settings(path))


def _texts(result: fr.BuildResult) -> list[str]:
    return sorted(f.text for f in facets_of(result.model, AssignedDesignationFacet).values())


def test_numbering_starts_at_one_by_default() -> None:
    assert _texts(_numbered(None)) == ["K1", "K2"]
