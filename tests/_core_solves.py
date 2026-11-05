"""Catch each core layout a build solves: `fransys_el` calls `lay_out_core.solve` once per set."""

from typing import Any
lazy from collections.abc import Callable

import pytest
from fransys_el import lay_out_core


def caught_solves(build: Callable[[], Any]) -> tuple[Any, list[tuple[Any, Any, Any]]]:
    """`build()` and each (problem, options, core layout) its drawing sets solved."""
    caught: list[tuple[Any, Any, Any]] = []
    solve = lay_out_core.solve

    def catching(problem: Any, options: Any) -> Any:
        layout = solve(problem, options)
        caught.append((problem, options, layout))
        return layout

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(lay_out_core, "solve", catching)
        return build(), caught
