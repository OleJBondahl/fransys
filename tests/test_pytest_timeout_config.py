"""The pytest-timeout plugin is pinned and capped in the root pyproject (decision 0222)."""

import importlib.util
import tomllib
from pathlib import Path

data = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8"))


def test_the_timeout_plugin_is_installed_and_pinned():
    assert "pytest-timeout==2.4.0" in data["dependency-groups"]["dev"], (
        "pytest-timeout==2.4.0 is missing from [dependency-groups] dev in the root pyproject.toml; "
        "add that exact pin, then run uv sync"
    )
    assert importlib.util.find_spec("pytest_timeout") is not None, (
        "the pytest_timeout plugin is not importable; run uv sync so the dev group installs it"
    )


def test_the_global_cap_is_set_and_charges_the_test_function_only():
    ini = data["tool"]["pytest"]["ini_options"]
    timeout = ini["timeout"]
    assert type(timeout) is int, (
        "[tool.pytest.ini_options] timeout must be an int number of seconds; "
        "set it to the global cap (180) in the root pyproject.toml"
    )
    assert timeout >= 60, (
        "[tool.pytest.ini_options] timeout must be an int of at least 60 seconds; "
        "set it to the global cap (180) in the root pyproject.toml"
    )
    assert ini["timeout_func_only"] is True, (
        "[tool.pytest.ini_options] timeout_func_only must be true so a module fixture's build "
        "is not charged to its first test; set it in the root pyproject.toml"
    )
