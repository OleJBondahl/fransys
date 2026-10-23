"""Reads one corpus instance into the contract's `fransys_layout.core.Scene`.

The one copy of the dump-line reader: `internal/placement_research/` imports it by path.

It parses the `today`, `route` and `marker` lines. It reads `sym`, `pin` and `net` lines only as
far as the scene needs: a box's body and pins at their absolute places, each pin's net and node.
Of the `fact` lines it reads `boxpin`, `attached`, `head` and `strip`, the flags the P rules read.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from fransys_layout.core import Box, Orientation, Side, Size
from fransys_layout.core.outputs import Scene, SceneBox, SceneMarker, ScenePin, SceneWire
from fransys_layout.core.values import MarkerKind, RefKind

CORPUS = Path(__file__).parent.parent / "corpus" / "placement"
KIND: dict[str, MarkerKind] = {
    "-": RefKind.TAG,
    "REF": RefKind.STAR,
    "BRANCH": RefKind.STAR,
    "OFF": RefKind.STUB,
}
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


SCENE_ORIENT: dict[str, Orientation] = {"R0": "R0", "R180": "R180", "MR180": "MR180"}


def _scene_orient(words: list[str]) -> Orientation:
    name = _kv(words)["orient"]
    if name not in SCENE_ORIENT:
        msg = f"corpus: unknown orient {name!r}"
        raise ValueError(msg)
    return SCENE_ORIENT[name]


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


def _flip(side: str, sx: int, sy: int) -> Side:
    swap = {"N": "S", "S": "N"} if sy < 0 else {}
    swap |= {"E": "W", "W": "E"} if sx < 0 else {}
    return cast("Side", swap.get(side, side))


def _pin(
    sid: str, pw: list[str], origin: tuple[int, int], turn: tuple[int, int], ctx: tuple
) -> ScenePin:
    net_of, facts = ctx
    dx, dy = _ints(pw[3])
    kv = _kv(pw)
    ref = f"{sid}.{pw[1]}"
    node = int(kv["node"]) if "node" in kv else None
    return ScenePin(
        pw[1],
        origin[0] + turn[0] * dx,
        origin[1] + turn[1] * dy,
        _flip(pw[2], *turn),
        net_of.get(ref),
        node,
        "stand" in kv,
        ref in facts.boxpin,
        sid in facts.head,
    )


def _box(sid: str, sym: Sym, words: list[str], page: int, ctx: tuple) -> SceneBox:
    turn = TURN[_kv(words)["orient"]]
    ox, oy = _ints(_kv(words)["at"])
    origin = (ox, oy)
    pins = tuple(_pin(sid, pw, origin, turn, ctx) for pw in sym.pins)
    bx, by, bw, bh = sym.body
    xs = sorted((origin[0] + turn[0] * bx, origin[0] + turn[0] * (bx + bw)))
    ys = sorted((origin[1] + turn[1] * by, origin[1] + turn[1] * (by + bh)))
    facts = ctx[1]
    body = Box(xs[0], ys[0], xs[1] - xs[0], ys[1] - ys[0])
    return SceneBox(
        sid,
        page,
        body,
        body,
        pins,
        sid in facts.attached,
        facts.strip.get(sid),
        _scene_orient(words),
    )


def read_instance(path: Path) -> Instance:
    return read_text(path.read_text(encoding="utf-8"), path.name)


def read_scene(text: str) -> Scene:
    """The scene of an instance text, for the research reader."""
    return read_text(text, "<text>").scene


def read_text(text: str, name: str) -> Instance:
    by_kind = _lines(text)
    syms = _syms(text)
    net_of, rails = _nets(by_kind.get("net", []))
    today = by_kind.get("today", [])
    if unknown := {w[1] for w in today} - set(syms):
        msg = f"{name}: today line for unknown symbol {sorted(unknown)}"
        raise ValueError(msg)
    # a page that holds only routes or markers still gets its number (CORPUS-PANEL-2)
    keyed = today + by_kind.get("route", []) + by_kind.get("marker", [])
    number = {k: i for i, k in enumerate(sorted({_key(w) for w in keyed}))}
    ctx = (net_of, _facts(by_kind))
    boxes = [_box(w[1], syms[w[1]], w, number[_key(w)], ctx) for w in today]
    wires = [
        SceneWire(w[1], number[_key(w)], tuple((x, y) for x, y in map(_ints, w[6:])), 1, "straight")
        for w in by_kind.get("route", [])
    ]
    markers = []
    for w in by_kind.get("marker", []):
        sid, pin = _owner(w[2], syms)
        x, y = _ints(_kv(w)["at"])
        markers.append(
            SceneMarker(w[1], KIND[_kv(w)["star"]], number[_key(w)], x, y, sid, pin, "", "N")
        )
    pages: dict[str, set[int]] = {}
    for b in boxes:
        pages.setdefault(b.sym, set()).add(b.page)
    unplaced = frozenset(set(syms) - set(pages))
    area = _ints(",".join(by_kind["area"][0][1:3]))
    scene = Scene(
        Size(*area),
        len({b.page for b in boxes}),
        tuple(boxes),
        tuple(wires),
        tuple(markers),
        frozenset(rails),
        (),
        (),
        (),
        (),  # a dump of today's engine has no rows: a page is one row
    )
    return Instance(scene, pages, unplaced)


def corpus_names() -> list[str]:
    return sorted(p.name.removesuffix(".score.json") for p in CORPUS.glob("*.score.json"))


def resided_names() -> frozenset[str]:
    """The instances whose card pins were moved to the half split (BOX-SIDES Q1).

    Their `today` and `route` lines stay as exported, so only pin-position checks skip them.
    """
    return frozenset((CORPUS / "resided.names").read_text(encoding="utf-8").split())


def read_score(name: str) -> dict:
    return json.loads((CORPUS / f"{name}.score.json").read_text(encoding="utf-8"))
