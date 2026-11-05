"""Run in its own context by `test_rule_rank_invariance.py`: every build under one id salt.

`run(salt)` sets the id namespace (`-` keeps the default), solves each build with its core layouts
caught, and returns each layout's `outcome` with the salted text of every id taken out, so two
"""

import importlib
import re
from contextlib import nullcontext
from contextvars import Context
from typing import Any

from _core_solves import caught_solves
from _rank_outcome import outcome
from _reference_lane_runner import _cases

from fransys_model.kernel import id_namespace

_HASH = re.compile(r"[0-9a-f]{32}")


def _plain(counter: Any) -> list[str]:
    """The sorted entries of an outcome multiset without any 32-hex id text."""
    return sorted(_HASH.sub("#", f"{k}*{n}") for k, n in counter.items())


def run(salt: str, name: str) -> list[Any]:
    """Per set of build `name`: the outcome of its layout with id hashes removed.

    It runs in an empty context, so `-` draws the real default ids even under a sweep salt.
    """
    return Context().run(_run, salt, name)


def _run(salt: str, name: str) -> list[Any]:
    with id_namespace(salt) if salt != "-" else nullcontext():
        return _salted(name)


def _salted(name: str) -> list[Any]:
    ring = importlib.import_module("ring_cases")
    builds = {**_cases(), "bank40": lambda: ring.bank_model(40)}
    _, caught = caught_solves(builds[name])
    return [{k: _plain(v) if hasattr(v, "items") else v for k, v in outcome(lay).items()} for _, _, lay in caught]
