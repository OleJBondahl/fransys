"""WHERE-WIRED (R652): a terminal wired to functions of several sets of its document is drawn in each.

Checked on the six corpus builds: the count of terminal copies (functions drawn in a set beyond their
own), no net left undrawn, and no more wire-over-marker findings than the base had.
"""

import importlib
import tomllib
from pathlib import Path

import pytest
from gate_scan import stock

from fransys_model.derive import (
    function_abroad,
    function_replicas,
    function_role,
    function_scopes,
    item_functions,
)

pytestmark = pytest.mark.private_input

ROOT = Path(__file__).resolve().parent.parent
# RAIL-FLAG (R921, R935; owner 2026-10-25: an unflagged terminal draws as a terminal): machine_panel and panel_di16p 90 -> 136, +46 = the 46
# terminals the old guess hid and the declared flag leaves drawn, each with its copies (claude-tools/rail_guess_ids.py; .fransys/RAIL-CLASSES.md)
COPIES = {"distribution_board": 0, "machine_panel": 136, "mcc": 38, "panel_di16p": 136, "remote_io": 30, "skid": 0}
STOCK = tomllib.loads((ROOT / "tests/ratchets.toml").read_text())["drawing_connection_not_drawn"]  # KI-132


def _build(name: str):
    run = importlib.import_module("placement_corpus.run")
    every = [*run.circuits("standard"), ("skid", run.load(run.SKID, "demo_skid"), {}, {})]
    return run.build(name, next(c for c in every if c[0] == name))


@pytest.fixture(scope="module", params=sorted(COPIES))
def built(request):
    return request.param, _build(request.param)


@pytest.mark.rule("WHERE-WIRED")
def test_each_terminal_wired_into_other_sets_is_drawn_in_them(built) -> None:
    name, result = built
    model = result.model
    extra = sum(len(function_scopes(model, f)) - 1 for fs in item_functions(model).values() for f in fs)
    assert extra == COPIES[name]


@pytest.mark.rule("WHERE-WIRED")
def test_a_function_that_is_not_a_terminal_is_drawn_in_its_own_set_only(built) -> None:
    _, result = built
    model = result.model
    others = [f for fs in item_functions(model).values() for f in fs if not function_role(model, f).terminal]
    assert others
    assert all(len(function_scopes(model, f)) == 1 for f in others)


@pytest.mark.rule("WHERE-WIRED")
def test_the_copies_leave_no_connection_undrawn_and_no_more_wire_over_marker(built) -> None:
    name, result = built
    assert sum(f.code == "CONNECTION_NOT_DRAWN" for f in result.findings) <= STOCK[name]  # the copies add none to the KI-132 stock
    over = sum(int(f.message.split()[0]) for f in result.findings if f.code == "WIRE_OVER_MARKER")
    assert over <= stock("drawing_wire_over_marker", name)


@pytest.mark.rule("G09-PAGE")
def test_only_a_replica_printed_in_another_document_keeps_its_stub(built) -> None:
    """The corpus prints each unit in its own document set: no end is abroad, so none keeps a stub (R895).

    The field case holds the cross-document end.
    """
    _, result = built
    model = result.model
    functions = [f for fs in item_functions(model).values() for f in fs]
    assert all(function_abroad(model, f) <= function_replicas(model, f) for f in functions)
    assert not any(function_abroad(model, f) for f in functions)
