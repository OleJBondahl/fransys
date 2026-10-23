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


def _item(name: str, *, marked: bool = False) -> SimpleNamespace:
    added: list[object] = []
    return SimpleNamespace(
        path=Path("/x") / name,
        get_closest_marker=lambda marker: (
            object() if marked and marker == "private_input" else None
        ),
        add_marker=added.append,
        added=added,
    )


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


def _skips(monkeypatch, *, export: bool) -> list[bool]:
    """Whether each of (a private_input item, a plain item) was given a skip marker."""
    monkeypatch.setattr(conftest, "is_export", lambda: export)
    items = [_item("test_a.py", marked=True), _item("test_b.py")]
    conftest.pytest_collection_modifyitems(SimpleNamespace(), items)
    return [bool(i.added) for i in items]


def test_the_export_skips_a_private_input_item_and_only_that(monkeypatch):
    """R462: the skip is keyed on the missing `internal/` root, and only the marked item gets it."""
    assert _skips(monkeypatch, export=True) == [True, False]


def test_the_private_tree_skips_nothing(monkeypatch):
    assert _skips(monkeypatch, export=False) == [False, False]
