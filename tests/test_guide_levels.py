"""Each guide task shows an easy and an efficient level that build one model (EA14).

A python block whose first line is `# easy: <task>` or `# efficient: <task>` is a level of that
task. Each such block is self-contained: it imports `fransys as fr` and ends with the design
in `d`. The test runs both levels of a task in fresh namespaces, builds `fr.build(d)`, and
asserts one model digest.
"""

import re
from collections import defaultdict
from importlib.resources import files

import pytest

_FENCE = re.compile(r"```python\n(.*?)```", re.DOTALL)
_LEVEL = re.compile(r"\A# (easy|efficient): (.+)\n")
_PAGES = ("authoring", "units", "examples", "parts", "index")
_MIN_TASKS = {"authoring": 3, "units": 1, "examples": 1}


def tasks_of(markdown: str) -> dict[str, dict[str, str]]:
    """Task name to {level: block text}, from the level-marked blocks of `markdown`."""
    found: dict[str, dict[str, str]] = defaultdict(dict)
    for block in _FENCE.findall(markdown):
        match = _LEVEL.match(block)
        if match:
            level, task = match.groups()
            assert level not in found[task], f"task {task!r} has two {level} blocks"
            found[task][level] = block
    return dict(found)


def _page_text(page: str) -> str:
    return files("fransys").joinpath("guide", f"{page}.md").read_text(encoding="utf-8")


def _digest(block: str) -> str:
    import fransys as fr

    namespace: dict = {}
    exec(compile(block, "<guide level block>", "exec"), namespace, namespace)  # noqa: S102 (the page's own runnable block)
    return fr.build(namespace["d"]).model.digest


def _cases() -> list[tuple[str, str]]:
    return [(page, task) for page in _PAGES for task in tasks_of(_page_text(page))]


@pytest.mark.parametrize(("page", "task"), _cases(), ids=lambda v: v)
def test_both_levels_of_a_task_build_one_model(page, task, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    levels = tasks_of(_page_text(page))[task]
    assert set(levels) == {"easy", "efficient"}, f"{page}: task {task!r} has {sorted(levels)}"
    assert _digest(levels["easy"]) == _digest(levels["efficient"])


@pytest.mark.parametrize(("page", "minimum"), _MIN_TASKS.items())
def test_a_page_teaches_its_tasks_at_both_levels(page, minimum):
    assert len(tasks_of(_page_text(page))) >= minimum


def test_a_level_pair_that_differs_is_caught(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base = "import fransys as fr\nd = fr.design('demo_parts', place='C1')\n"
    one = base + "d.location('C1', 'One')\nd.device('X1', 'DEMO-TB-2.5')\n"
    other = base + "d.location('C1', 'One')\nd.device('X2', 'DEMO-TB-2.5')\n"
    assert _digest(one) != _digest(other)
