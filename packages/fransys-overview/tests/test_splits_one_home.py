"""The colour-split list is one list in Python (`_splits`); the page script's copy must equal it."""

import re

import pytest
from fransys_overview._app import APP_JS
from fransys_overview._splits import CLASS_SPLITS, NONE_SPLIT, SPLITS, classes_of


def _js_splits() -> list[list[str]]:
    (block,) = re.findall(r"const SPLITS = \[(.*?)\];", APP_JS, re.DOTALL)
    return [list(pair) for pair in re.findall(r"\['(\w+)', '([^']+)'\]", block)]


def _js_split_at() -> dict[str, int]:
    (block,) = re.findall(r"const SPLIT_AT = \{([^}]*)\};", APP_JS)
    return {key: int(index) for key, index in re.findall(r"(\w+): (\d+)", block)}


def test_the_script_splits_equal_the_python_list():
    assert _js_splits() == [list(pair) for pair in SPLITS]
    assert [split for split, _ in _js_splits()] == [NONE_SPLIT, *CLASS_SPLITS]


def test_the_script_class_slots_follow_the_python_order():
    assert _js_split_at() == {split: index for index, split in enumerate(CLASS_SPLITS)}


def test_classes_follow_the_class_split_order():
    values = {split: split.upper() for split in CLASS_SPLITS}
    assert classes_of(**values) == [split.upper() for split in CLASS_SPLITS]


def test_a_class_split_with_no_value_is_refused():
    values = dict.fromkeys(CLASS_SPLITS[1:])
    with pytest.raises(KeyError):
        classes_of(**values)
