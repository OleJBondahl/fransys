"""RANK-INVARIANCE harness: permute the ids of every kind of a placement problem.

`rename_problem(problem, mode)` maps the ids of each kind to a permutation of the same ids (mode
`reverse`: natural order reversed; `shuffle`: a hash order; `control`: a prefix that keeps every
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import fields, is_dataclass, replace
from typing import Any

from fransys_layout.core import PlacementProblem, natural_key

_PREFIX = "A"  # the control keeps every plain and natural comparison; "~" flipped some
Mapping_ = dict[str, str]

# (class, field) -> the id kind it defines; the walk reads these to build the mapping.
_DEFINES = {
    ("Sym", "id"): "sym",
    ("PinRef", "sym"): "sym",
    ("CutEnd", "line"): "line",  # a path: its `/` parts are the ids
    ("Net", "id"): "net",
    ("Bundle", "id"): "net",
    ("Unit", "id"): "unit",
    ("Sym", "group"): "group",
    ("Sym", "item"): "item",
    ("Sym", "child_of"): "child",
    ("Sym", "row_group"): "child",
}
# Pin names, sides, turns and spot names are no ids; they stay.
_NOT_IDS = {
    ("PinRef", "pin"),
    ("Series", "anchor"),
    ("Pin", "id"),
    ("BoxSpec", "order"),
    ("Sym", "nodes"),
    ("Pin", "side"),
    ("PinTurn", "side"),
    ("Bundle", "form"),
    ("Spot", "corner"),
    ("Spot", "name"),
    ("Spot", "grow"),
    ("Pose", "turn"),
    ("Anchor", "poses"),
}
_DERIVED = re.compile(r"^(?P<head>(?:[a-z]+:)+)(?P<id>.+?)(?P<tail>#[ab])?$")


def _is_plain_str(o: Any) -> bool:
    return type(o) is str  # enums are str subclasses and no ids


def _sets(problem: PlacementProblem) -> dict[str, set[str]]:
    """The ids each defining field holds, by kind, merged where two kinds share an id."""
    out: dict[str, set[str]] = {}

    def walk(o: Any) -> None:
        if is_dataclass(o) and not isinstance(o, type):
            for f in fields(o):
                v = getattr(o, f.name)
                kind = _DEFINES.get((type(o).__name__, f.name))
                if kind and isinstance(v, str) and v:
                    out.setdefault(kind, set()).update(v.split("/") if kind == "line" else [v])
                walk(v)
        elif isinstance(o, tuple | list | frozenset | set):
            for x in o:
                walk(x)

    walk(problem)
    merged: list[set[str]] = []
    for ids in out.values():
        hit = [m for m in merged if m & ids]
        merged = [m for m in merged if m not in hit]
        merged.append(ids.union(*hit))
    return {f"k{n}": ids for n, ids in enumerate(merged)}


def build_mapping(problem: PlacementProblem, mode: str = "reverse") -> Mapping_:
    """Per merged kind a permutation of its ids; `mode` picks which.

    `reverse`: the k-th id by natural key goes to the (n-1-k)-th. `shuffle`: to the k-th by a
    hash of the text, an order that also differs from the plain string order (raw str ties).
    """
    kinds = list(_sets(problem).values())
    if mode == "control":
        return {i: _PREFIX + i for ids in kinds for i in ids}
    mapping: Mapping_ = {}
    for ids in kinds:
        ordered = sorted(ids, key=natural_key)
        # S324: a fixed shuffle, not security
        target = list(reversed(ordered)) if mode == "reverse" else sorted(ids, key=lambda i: hashlib.sha1(i.encode()).hexdigest())  # noqa: S324
        mapping.update(zip(ordered, target, strict=True))
    return mapping


def _text(s: str, m: Mapping_) -> str | None:
    """The mapped spelling of `s`, or None when no part of it is a mapped id."""
    if s in m:
        return m[s]
    if "/" in s:
        parts = [m.get(p) for p in s.split("/")]
        if None not in parts:
            return "/".join(p for p in parts if p is not None)
    found = _DERIVED.match(s)
    if found and found["id"] in m:
        return str(found["head"] + m[found["id"]] + (found["tail"] or ""))
    return None


def _walk(o: Any, m: Mapping_, path: tuple[str, ...], gaps: set[tuple[str, ...]]) -> Any:
    if _is_plain_str(o):
        out = _text(o, m)
        if out is None and o and tuple(path[-2:]) not in _NOT_IDS and path[-1:] != ("{key}",):
            gaps.add((*path, o))
        return o if out is None else out
    if is_dataclass(o) and not isinstance(o, type):
        name = type(o).__name__
        changed = {f.name: _walk(getattr(o, f.name), m, (*path[-1:], name, f.name), gaps) for f in fields(o) if f.init}
        return replace(o, **changed)
    if isinstance(o, tuple):
        return tuple(_walk(x, m, path, gaps) for x in o)
    if isinstance(o, frozenset):
        return frozenset(_walk(x, m, path, gaps) for x in o)
    if hasattr(o, "items"):
        items = {_walk(k, m, ("{key}",), gaps): _walk(v, m, path, gaps) for k, v in o.items()}
        return type(o)(items)
    return o


def apply_mapping(value: Any, mapping: Mapping_) -> tuple[Any, set[tuple[str, ...]]]:
    """`value` with every id respelled, and the (path, string) pairs the walk could not place."""
    gaps: set[tuple[str, ...]] = set()
    return _walk(value, mapping, (), gaps), gaps


def rename_problem(problem: PlacementProblem, mode: str = "reverse") -> tuple[Any, Mapping_]:
    """`problem` with every id kind permuted by `mode`, and the old-to-new mapping.

    Ids derived inside the core (`c:<sym>`, `f:<net>`, blocks) follow their parts. `control`
    prefixes each id instead, keeping every order: a run on it must equal the original, which
    """
    mapping = build_mapping(problem, mode)
    renamed, gaps = apply_mapping(problem, mapping)
    assert not gaps, f"ids the harness cannot reach: {sorted(gaps)[:10]}"
    return renamed, mapping


def unrename(value: Any, mapping: Mapping_) -> Any:
    """`value` (a layout or a part of it) with the renamed ids mapped back."""
    inverse = {new: old for old, new in mapping.items()}
    return apply_mapping(value, inverse)[0]


def check_all_mapped(problem: PlacementProblem, mapping: Mapping_) -> None:
    """Every id string of `problem` is a key of `mapping`: a mapping that misses one is caught."""
    _, gaps = apply_mapping(problem, mapping)
    assert not gaps, f"ids with no mapping: {sorted(gaps)[:10]}"


def rename_options(options: Any, mapping: Mapping_) -> Any:
    """`options` with the ids it carries (the keys of `marker_fit`) respelled; other text stays."""
    return apply_mapping(options, mapping)[0]
