"""Run in its own context by `test_rule_bundle_reference_lane.py`: every build, one id salt.

`run(salt)` sets the id namespace (`-` keeps the default), then solves each build with its core
layouts caught. It returns, per build, the findings and the references whose ends sit on two nets.
"""

import importlib
import re
from collections import defaultdict
from contextlib import nullcontext
from typing import Any

import fransys as fr

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


def _cases() -> list[str]:
    """The names of the reference-lane cases: the standard circuits and the demo skid."""
    return [*(c[0] for c in importlib.import_module("placement_corpus.run").circuits("standard")), "demo-skid"]


def observation(case: str) -> Any:
    """The corpus build of `case` under the current id namespace, with what its run caught (R3302)."""
    return importlib.import_module("placement_corpus.run").observed("skid" if case == "demo-skid" else case)


def _lanes(case: str) -> tuple[Any, list[Any], list[Any], list[tuple[str, bool]]]:
    """The build of `case`, its solves, the lane cells of every flow, and the TAG and STUB ends stage 4 made, pinless or not (R2041 G1)."""
    seen = observation(case)
    hexid = re.compile(r"[0-9a-f]{32}")
    lanes = [[hexid.sub("", sym) for sym in flow] for flow in seen.caught("flows")]
    return seen.result, seen.caught("solves"), lanes, [mark for call in seen.caught("references") for mark in call]


def run(salt: str, case: str) -> dict[str, Any]:
    """One case built under `salt`, as plain values."""
    with id_namespace(salt) if salt != "-" else nullcontext():
        built, caught, lanes, marked = _lanes(case)
    return {
        "shorts": sum(f.code == "DRAWING_SHORTS_NETS" for f in built.findings),
        "errors": [f.code for f in built.findings if f.severity == fr.Severity.ERROR],
        "split": [s for p, _, lay in caught for s in _split_references(p, lay)],
        "lanes": lanes,
        "tag_ends": len(marked),
        "pinless": [name for name, none in marked if none],
        "markers": sum(len(lay.annotations.markers) for _, _, lay in caught),
    }
