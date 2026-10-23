"""Builds the settings-text override tests share: the demo skid under a consumer's settings file."""

import importlib.util
from functools import cache
from pathlib import Path

import fransys as fr

lazy from fransys_model.kernel import Model

_SKID = Path(__file__).parents[3] / "examples" / "demo-skid" / "skid.py"


def consumer_file(tmp_path: Path, text: str) -> Path:
    """A `fransys.toml` holding `text`."""
    path = tmp_path / "fransys.toml"
    path.write_text(text, encoding="utf-8")
    return path


@cache
def _skid_design() -> tuple:
    spec = importlib.util.spec_from_file_location("skid_for_settings_text", _SKID)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    made = module.design()
    return made if isinstance(made, tuple) else (made,)


def skid_model(path: Path | None = None) -> Model:
    """The demo skid built with `fr.settings(path)`; `None` is the house settings."""
    return fr.build(*_skid_design(), settings=fr.settings(path)).model
