"""`d.layout.profile` names each profile field with its type: no `**numbers` (EA15)."""

import dataclasses
import inspect
from typing import Any
lazy from collections.abc import Callable

import fransys as fr
import pytest

from fransys_model.layout import Profile, default_profile, profile_of

_NOT_TUNABLE = {"id", "key", "sheet_format", "ext"}


def _profile_call() -> Callable[..., Any]:
    return fr.design("demo_parts").layout.profile


def test_signature_lists_every_profile_field() -> None:
    """The keywords are `sheet` and each tunable `Profile` field; none is var-keyword."""
    params = inspect.signature(_profile_call()).parameters
    fields = {f.name for f in dataclasses.fields(Profile)} - _NOT_TUNABLE
    assert set(params) == {"sheet", *fields}
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in params.values())
    assert "bool" in str(params["hide_unused_pins"].annotation)


def test_unknown_keyword_raises_type_error() -> None:
    """A field the model lacks is a TypeError at the call, not an engine message at build."""
    d = fr.design("demo_parts")
    with pytest.raises(TypeError, match="wobble_factor"):
        d.layout.profile(wobble_factor=9)  # ty: ignore[unknown-argument] -- the planted error


def test_given_values_reach_the_profile() -> None:
    """A number, a flag and a plain dict rank map are stored; the rest keep the house value."""
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    d.layout.profile(
        column_gap=40, hide_unused_pins=True, band_ranks={"SIGNAL": 2}, group_ranks={"FEED": 1}
    )
    profile = profile_of(fr.build(d).model)
    assert (profile.column_gap, profile.hide_unused_pins) == (40, True)
    assert dict(profile.band_ranks) == {"SIGNAL": 2}
    assert dict(profile.group_ranks) == {"FEED": 1}
    assert profile.row_gap == default_profile().row_gap
