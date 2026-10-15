"""Reads one corpus instance into a `fransys_layout.core.Scene`.

It parses the `today`, `route` and `marker` lines. It reads `sym`, `pin` and `net` lines only as
far as the scene needs: a box's body and pins at their absolute places, each pin's net and node.
Of the `fact` lines it reads `boxpin`, `attached`, `head` and `strip`, the flags the P rules read.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from fransys_layout.core import Box, Marker, Pin, Scene, Wire

CORPUS = Path(__file__).parent.parent / "corpus" / "placement"
CLASS = {"-": "tag_pair", "REF": "star", "BRANCH": "star", "OFF": "stub"}
TURN = {"R0": (1, 1), "R180": (-1, -1), "MR180": (1, -1)}  # orientation -> (sx, sy) on R0 offsets


@dataclass
class Instance:
    scene: Scene
    box_pages: dict[str, set[int]]  # symbol id -> the pages its copies stand on
    unplaced: frozenset[str]  # drawn symbols today never placed (the original of a copied function)


@dataclass
class Sym:
    body: tuple[int, int, int, int]
    pins: list[list[str]]


def _kv(tokens: list[str]) -> dict[str, str]:
    return dict(t.split("=", 1) for t in tokens if "=" in t)


def _ints(text: str) -> tuple[int, ...]:
    return tuple(int(v) for v in text.split(","))


def _key(words: list[str]) -> tuple[int, int]:
    kv = _kv(words)
    return int(kv["set"]), int(kv["page"])


def _lines(text: str) -> dict[str, list[list[str]]]:
    out: dict[str, list[list[str]]] = {}
    for line in text.splitlines():
        if line.strip() and not line.startswith("#"):
            words = line.split()
            out.setdefault(words[0], []).append(words)
    return out


def _syms(text: str) -> dict[str, Sym]:
    out: dict[str, Sym] = {}
    last = ""
    for words in (ln.split() for ln in text.splitlines() if ln.split()[:1] in (["sym"], ["pin"])):
        if words[0] == "sym":
            last = words[1]
            x, y, w, h = _ints(_kv(words)["body"])
            out[last] = Sym((x, y, w, h), [])
        else:
            out[last].pins.append(words)
    return out


def _owner(ref: str, syms: dict[str, Sym]) -> tuple[str, str]:
    """Split "SYM.PIN" at the dot after the longest symbol id that prefixes it."""
    sid = max((s for s in syms if ref.startswith(s + ".")), key=len)
    return sid, ref[len(sid) + 1 :]


def _nets(lines: list[list[str]]) -> tuple[dict[str, str], set[str]]:
    net_of: dict[str, str] = {}
    rails: set[str] = set()
    for words in lines:
        if "[rail" in words:
            rails.add(words[1])
        for w in words[2:]:
            if "." in w and not w.startswith(("[", "rank=", "power=")):
                net_of[w] = words[1]
    return net_of, rails


@dataclass
class Facts:
    boxpin: set[str]
    attached: set[str]
    head: set[str]
    strip: dict[str, str]  # symbol id -> strip tag


def _facts(by_kind: dict[str, list[list[str]]]) -> Facts:
    flags: dict[str, set[str]] = {"boxpin": set(), "attached": set(), "head": set()}
    strip: dict[str, str] = {}
    for words in by_kind.get("fact", []):
        if words[1] in flags:
            flags[words[1]].update(words[2:])
        elif words[1] == "strip":
            strip.update(dict.fromkeys(words[3:], words[2]))
    return Facts(flags["boxpin"], flags["attached"], flags["head"], strip)


def _flip(side: str, sx: int, sy: int) -> str:
    swap = {"N": "S", "S": "N"} if sy < 0 else {}
    swap |= {"E": "W", "W": "E"} if sx < 0 else {}
    return swap.get(side, side)


def _pin(
    sid: str, pw: list[str], origin: tuple[int, int], turn: tuple[int, int], ctx: tuple
) -> Pin:
    net_of, facts = ctx
    dx, dy = _ints(pw[3])
    kv = _kv(pw)
    ref = f"{sid}.{pw[1]}"
    node = int(kv["node"]) if "node" in kv else None
    return Pin(
        pw[1],
        origin[0] + turn[0] * dx,
        origin[1] + turn[1] * dy,
        net_of.get(ref),
        node,
        "stand" in kv,
        _flip(pw[2], *turn),
        ref in facts.boxpin,
    )


def _box(sid: str, sym: Sym, words: list[str], page: int, ctx: tuple) -> Box:
    turn = TURN[_kv(words)["orient"]]
    ox, oy = _ints(_kv(words)["at"])
    origin = (ox, oy)
    pins = tuple(_pin(sid, pw, origin, turn, ctx) for pw in sym.pins)
    bx, by, bw, bh = sym.body
    xs = sorted((origin[0] + turn[0] * bx, origin[0] + turn[0] * (bx + bw)))
    ys = sorted((origin[1] + turn[1] * by, origin[1] + turn[1] * (by + bh)))
    facts = ctx[1]
    return Box(
        sid,
        page,
        xs[0],
        ys[0],
        xs[1] - xs[0],
        ys[1] - ys[0],
        pins,
        sid in facts.attached,
        sid in facts.head,
        facts.strip.get(sid),
    )


def read_instance(path: Path) -> Instance:
    text = path.read_text(encoding="utf-8")
    by_kind = _lines(text)
    syms = _syms(text)
    net_of, rails = _nets(by_kind.get("net", []))
    today = by_kind.get("today", [])
    assert {w[1] for w in today} <= set(syms), path.name
    number = {k: i for i, k in enumerate(sorted({_key(w) for w in today}))}
    ctx = (net_of, _facts(by_kind))
    boxes = [_box(w[1], syms[w[1]], w, number[_key(w)], ctx) for w in today]
    wires = [
        Wire(w[1], number[_key(w)], tuple((x, y) for x, y in map(_ints, w[6:])))
        for w in by_kind.get("route", [])
    ]
    markers = []
    for w in by_kind.get("marker", []):
        sid, pin = _owner(w[2], syms)
        markers.append(Marker(w[1], sid, pin, number[_key(w)], CLASS[_kv(w)["star"]]))
    pages: dict[str, set[int]] = {}
    for b in boxes:
        pages.setdefault(b.id, set()).add(b.page)
    unplaced = frozenset(set(syms) - set(pages))
    scene = Scene(tuple(boxes), tuple(wires), tuple(markers), frozenset(rails))
    return Instance(scene, pages, unplaced)


def corpus_names() -> list[str]:
    return sorted(p.name.removesuffix(".score.json") for p in CORPUS.glob("*.score.json"))


def read_score(name: str) -> dict:
    return json.loads((CORPUS / f"{name}.score.json").read_text(encoding="utf-8"))
