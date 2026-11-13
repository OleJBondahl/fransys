"""Run in its own context by `test_rule_bundle_reference_lane.py`: every build, one id salt.

`run(salt)` sets the id namespace (`-` keeps the default), then solves each build with its core
layouts caught. It returns, per build, the findings and the references whose ends sit on two nets.
"""

import importlib
import re
import sys
from collections import defaultdict
from contextlib import nullcontext
from typing import Any

import fransys as fr
import pytest
from _core_solves import caught_solves

from fransys_model.kernel import id_namespace


def _split_references(problem: Any, layout: Any) -> list[str]:
    """Each reference (net, cut, kind) whose marker ends name pins of more than one net.

    A fan's reference carries the fan id, so its ends are compared with each other, not with it;
    a stub has one end and no partner.
    """
    net_of = {pin: n.id for n in problem.nets for pin in n.pins}
    ends: dict[Any, set[str | None]] = defaultdict(set)
    for m in layout.annotations.markers:
        if str(m.kind) == "stub":
            continue
        ends[(m.net, m.ref, str(m.kind))].add(net_of.get(m.end))
    return [f"{k}: {sorted(map(str, v))}" for k, v in ends.items() if len(v) != 1 or None in v]


def _cases() -> dict[str, Any]:
    run = importlib.import_module("placement_corpus.run")
    cases: dict[str, Any] = {c[0]: (lambda c=c: run.build(c[0], c, fresh=True)) for c in run.circuits("standard")}
    skid: Any = (run.SKID.name, run.load(run.SKID, "demo_skid_lane"), {}, {})
    cases["demo-skid"] = lambda: run.build("demo-skid", skid, fresh=True)
    return cases


def _lanes(build: Any) -> tuple[Any, list[Any], list[Any], list[tuple[str, bool]]]:
    """`build()` with its solves caught, the lane cells of every flow, and the TAG and STUB ends stage 4 made, pinless or not (R2041 G1)."""
    solve = sys.modules["fransys_layout.core.solve"]
    cut = sys.modules["fransys_layout.core.cut"]
    made: list[Any] = []
    marked: list[tuple[str, bool]] = []
    flow, references = solve.build_flow, cut.references

    def building(*args: Any) -> Any:
        made.append(flow(*args))
        return made[-1]

    def noting(*args: Any) -> Any:
        refs = references(*args)
        marked.extend((f"{r.net} {r.kind}", e.pin is None) for r in refs if str(r.kind) in ("tag", "stub") for e in r.ends)
        return refs

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(solve, "build_flow", building)
        patch.setattr(cut, "references", noting)
        built, caught = caught_solves(build)
    hexid = re.compile(r"[0-9a-f]{32}")
    return built, caught, [[hexid.sub("", c.sym) for col in f.columns for lane in col.lanes for c in lane.cells] for f in made], marked


def run(salt: str, case: str) -> dict[str, Any]:
    """One case built under `salt`, as plain values."""
    with id_namespace(salt) if salt != "-" else nullcontext():
        built, caught, lanes, marked = _lanes(_cases()[case])
    return {
        "shorts": sum(f.code == "DRAWING_SHORTS_NETS" for f in built.findings),
        "errors": [f.code for f in built.findings if f.severity == fr.Severity.ERROR],
        "split": [s for p, _, lay in caught for s in _split_references(p, lay)],
        "lanes": lanes,
        "tag_ends": len(marked),
        "pinless": [name for name, none in marked if none],
        "markers": sum(len(lay.annotations.markers) for _, _, lay in caught),
    }
