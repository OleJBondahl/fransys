"""The root `conftest.py` gives each scale-count module a worker slice start; others keep order."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

_spec = importlib.util.spec_from_file_location(
    "scale_first_conftest", Path(__file__).parents[1] / "conftest.py"
)
assert _spec is not None
assert _spec.loader is not None
conftest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(conftest)


def _item(name: str) -> SimpleNamespace:
    return SimpleNamespace(path=Path("/x") / name)


def _order(workers: int | None, names: list[str]) -> list[str]:
    config = SimpleNamespace()
    if workers is not None:
        config.workerinput = {"workercount": workers}
    items = [_item(n) for n in names]
    conftest.pytest_collection_modifyitems(config, items)
    return [i.path.name for i in items]


_MIXED = [
    "test_a.py",
    "test_render_scale_counts.py",
    "test_b.py",
    "test_scale_call_counts.py",
    "test_c.py",
    "test_d.py",
]


def test_without_xdist_the_scale_modules_lead():
    assert _order(None, _MIXED) == [
        "test_render_scale_counts.py",
        "test_scale_call_counts.py",
        "test_a.py",
        "test_b.py",
        "test_c.py",
        "test_d.py",
    ]


def test_with_workers_each_scale_module_starts_a_slice():
    # 6 items over 3 workers: slices of 2, so the modules sit at index 0 and 2
    assert _order(3, _MIXED) == [
        "test_scale_call_counts.py",
        "test_a.py",
        "test_render_scale_counts.py",
        "test_b.py",
        "test_c.py",
        "test_d.py",
    ]
