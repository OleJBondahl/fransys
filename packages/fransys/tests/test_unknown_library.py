"""An unknown part library names itself and the libraries already loaded (BUILD-MESSAGES M3)."""

import fransys as fr
import pytest


def test_parts_names_the_missing_library_and_the_loaded_ones() -> None:
    fr.parts("demo_parts")
    with pytest.raises(
        ModuleNotFoundError,
        match=r"no part library .no_such_lib.*loaded in this process: .*demo_parts",
    ):
        fr.parts("no_such_lib")


def test_lint_and_design_say_the_same() -> None:
    with pytest.raises(ModuleNotFoundError, match="no part library 'no_such_lib'"):
        fr.lint("no_such_lib")
    with pytest.raises(ModuleNotFoundError, match="no part library 'no_such_lib'"):
        fr.design("no_such_lib")
