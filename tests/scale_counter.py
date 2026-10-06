"""Execution counts of `fransys_layout` and `fransys_render` code on the scale fixture.

One harness for both counts: D10's Check (layout-0086) and RW3 (render-0006). `count_render(n)`
counts `fransys_render.pages` on `build_scale(n, with_document=True)`, no pass normalisation.

`count_build(n)` runs `build_scale(n)` under stdlib `sys.monitoring` and counts, per code object of
`fransys_layout`, calls (PY_START), generator resumes (PY_RESUME) and loop iterations (JUMP).
The key is `file:qualname:firstlineno`, the file relative to the `fransys_layout/` folder with
forward slashes. Counts of events that happen while a `stages/pagerun.py:_place_each` call is on
the stack are divided by the number of such calls (a "pass"); events outside a pass count whole.

Stated limit: a C-level scan (`x in a_tuple`, `sorted`) is seen only through a Python callee.

`build_scale`'s own default stays document-free (MODEL-BUILD acceptance 6); decision 0037 (PS1)
gates layout on a document, so counting real `fransys_layout` calls needs
`build_scale(n, with_document=True)` instead -- this module's own build, never `build_scale`'s
default.
"""

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

import fransys_render
from scale_units_fixture import build_scale

from fransys_layout.stages import pagerun

if TYPE_CHECKING:
    from collections.abc import Callable

_LAYOUT_MARK = "/fransys_layout/"
_RENDER_MARK = "/fransys_render/"
_PASS_CODE = pagerun._place_each.__code__


@dataclass(frozen=True)
class BuildCounts:
    """Pass count and the pass-normalised counts per key, for one `build_scale(n)`."""

    passes: int
    jumps: dict[str, float]
    calls: dict[str, float]
    resumes: dict[str, float]


def check_passes(small: BuildCounts, big: BuildCounts) -> None:
    """The pass normalisation is only comparable when both sizes ran the same number of passes."""
    if small.passes != big.passes:
        message = f"_place_each ran {small.passes} times at N but {big.passes} times at 2N"
        raise AssertionError(message)


def flagged(
    small: dict[str, float],
    big: dict[str, float],
    *,
    threshold: float = 2.5,
    floor: int = 100,
) -> dict[str, float]:
    """Key -> count(2N)/count(N) for keys with count(2N) >= floor and a ratio above threshold."""
    out = {}
    for key, count in big.items():
        if count >= floor:
            base = small.get(key, 0)
            ratio = count / base if base else float("inf")
            if ratio > threshold:
                out[key] = ratio
    return out


def _key(code, mark: str) -> str:
    rel = code.co_filename.replace("\\", "/").split(mark, 1)[1]
    return f"{rel}:{code.co_qualname}:{code.co_firstlineno}"


class _Monitor:
    """One `sys.monitoring` session: three count dicts per bucket (outside, then one per pass)."""

    def __init__(self, tool: int, mark: str, pass_code=None) -> None:
        self.tool = tool
        self.mark = mark
        self.pass_code = pass_code  # None: no pass, every event counts whole
        self.seen: dict = {}  # code object -> is package code
        self.outside: tuple[dict, dict, dict] = ({}, {}, {})  # calls, resumes, jumps
        self.passes: list[tuple[dict, dict, dict]] = []
        self.cur = self.outside

    def is_ours(self, code) -> bool:
        if code not in self.seen:
            self.seen[code] = self.mark in code.co_filename.replace("\\", "/")
            if self.seen[code]:
                sys.monitoring.set_local_events(self.tool, code, sys.monitoring.events.JUMP)
        return self.seen[code]

    def bump(self, i: int, code) -> None:
        self.cur[i][code] = self.cur[i].get(code, 0) + 1

    def on_start(self, code, _offset) -> None:
        if code is self.pass_code:
            self.cur = ({}, {}, {})
            self.passes.append(self.cur)
        if self.is_ours(code):
            self.bump(0, code)

    def on_resume(self, code, _offset) -> None:
        if self.is_ours(code):
            self.bump(1, code)

    def on_jump(self, code, _offset, _dest) -> None:
        self.bump(2, code)

    def on_end(self, _code, _offset, _value) -> None:
        self.cur = self.outside

    def run(self, work: Callable[[], object]) -> None:
        mon, ev, tool = sys.monitoring, sys.monitoring.events, self.tool
        try:
            for event, fn in (
                (ev.PY_START, self.on_start),
                (ev.PY_RESUME, self.on_resume),
                (ev.JUMP, self.on_jump),
                (ev.PY_RETURN, self.on_end),
                (ev.PY_UNWIND, self.on_end),
            ):
                mon.register_callback(tool, event, fn)
            if self.pass_code is not None:
                self.seen[self.pass_code] = True
                mon.set_local_events(tool, self.pass_code, ev.PY_RETURN | ev.PY_UNWIND | ev.JUMP)
            mon.set_events(tool, ev.PY_START | ev.PY_RESUME)
            work()
        finally:
            mon.set_events(tool, 0)
            for code, is_ours in self.seen.items():
                if is_ours:
                    mon.set_local_events(tool, code, 0)
            for event in (ev.PY_START, ev.PY_RESUME, ev.JUMP, ev.PY_RETURN, ev.PY_UNWIND):
                mon.register_callback(tool, event, None)

    def normalised(self, i: int) -> dict[str, float]:
        out: dict[str, float] = {}
        for code, count in self.outside[i].items():
            out[_key(code, self.mark)] = out.get(_key(code, self.mark), 0) + count
        for one in self.passes:
            for code, count in one[i].items():
                key = _key(code, self.mark)
                out[key] = out.get(key, 0) + count / len(self.passes)
        return out


def _monitored(mark: str, pass_code, work: Callable[[], object]) -> _Monitor:
    tool = 3
    try:
        sys.monitoring.use_tool_id(tool, "scale-count")
    except ValueError:
        tool = 4
        sys.monitoring.use_tool_id(tool, "scale-count")
    try:
        mon = _Monitor(tool, mark, pass_code)
        mon.run(work)
    finally:
        sys.monitoring.free_tool_id(tool)
    return mon


def _counts(mon: _Monitor) -> BuildCounts:
    return BuildCounts(len(mon.passes), mon.normalised(2), mon.normalised(0), mon.normalised(1))


def count_build(n: int) -> BuildCounts:
    """Count one `build_scale(n)`, after an uncounted `build_scale(2)` that fills module caches."""
    build_scale(2, with_document=True)
    return _counts(_monitored(_LAYOUT_MARK, _PASS_CODE, lambda: build_scale(n, with_document=True)))


def count_render(n: int) -> BuildCounts:
    """Count `fransys_render.pages` alone on `build_scale(n)`; the build is not monitored."""
    fransys_render.pages(build_scale(2, with_document=True).model)
    model = build_scale(n, with_document=True).model
    return _counts(_monitored(_RENDER_MARK, None, lambda: fransys_render.pages(model)))
