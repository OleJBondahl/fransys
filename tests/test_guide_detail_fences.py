"""Only `detail.md` and the moving-to pages show a detail call in a fence (decision 0194, A4).

The guide teaches the core calls first: a python block elsewhere that calls `d.detail.*` (on any
design, `u.detail.wire` too) would teach a consumer the detail call for a case a core call writes.
"""

import re
from importlib.resources import files

_FENCE = re.compile(r"```python\n(.*?)```", re.DOTALL)
_DETAIL_CALL = re.compile(r"\b\w+\.detail\.\w+\(")


def _allowed(page: str) -> bool:
    return page == "detail.md" or page.startswith("moving-to-")


def detail_calls_outside(pages: dict[str, str]) -> list[str]:
    """`page: call` for each detail call in a python fence of a page that may not show one."""
    return [
        f"{page}: {call.group(0)}"
        for page, text in sorted(pages.items())
        if not _allowed(page)
        for fence in _FENCE.findall(text)
        for call in _DETAIL_CALL.finditer(fence)
    ]


def _guide() -> dict[str, str]:
    guide = files("fransys").joinpath("guide")
    return {
        p.name: p.read_text(encoding="utf-8") for p in guide.iterdir() if p.name.endswith(".md")
    }


def test_no_fence_outside_detail_md_and_moving_to_calls_a_detail_call():
    assert not detail_calls_outside(_guide())


def test_the_gate_sees_a_detail_call_on_any_design_and_allows_its_two_homes():
    block = "```python\nu.detail.wire(a, b, wire=(BU, 0.75))\n```\n"
    assert detail_calls_outside({"authoring.md": block}) == ["authoring.md: u.detail.wire("]
    assert not detail_calls_outside({"detail.md": block, "moving-to-0.19.md": block})
    assert not detail_calls_outside({"authoring.md": "`d.detail.wire(a, b)` in prose\n"})
    assert "detail.md" in _guide()
