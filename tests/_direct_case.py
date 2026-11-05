"""Lay a built design out again from its unlaid model, for tests that compare with the facade (F7).

`fr.build` lays the model out once and keeps the Drawings in its memo. A test that wants an
independent run takes the model the facade handed the core layout step and calls `lay_out_drawn`.
"""

import tomllib
from pathlib import Path

import fransys as fr
import pytest
from fransys import _layout_need as layout_need
from fransys_el import build, house_conventions, lay_out_drawn, symbol_kit

import fransys_layout
from electrical_symbols import LIBRARY

LAYOUT = tomllib.loads((Path(fransys_layout.__file__).parent / "layout.toml").read_text(encoding="utf-8"))["layout"]


def built_with_unlaid(build_it):
    """(the `BuildResult`, the model the facade handed the core layout step with no records)."""
    seen = []
    real = layout_need.lay_out_on_core

    def spy(model, library, *rest, **kw):
        seen.append(model)
        return real(model, library, *rest, **kw)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(layout_need, "lay_out_on_core", spy)
        result = build_it()
    assert isinstance(result, fr.BuildResult)
    return result, seen[0]


def laid_again(unlaid):
    """`lay_out_drawn` over `unlaid` with the house conventions: (laid model, Drawings)."""
    conventions = house_conventions(fr.settings().layout, LIBRARY, text_height=8)
    kit = symbol_kit(unlaid, LIBRARY)
    problem, _ = build(unlaid, kit, conventions, LIBRARY)
    laid, _, drawn = lay_out_drawn(unlaid, kit, problem, conventions, LIBRARY)
    return laid, drawn
