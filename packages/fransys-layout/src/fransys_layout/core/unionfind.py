"""Union-find over string keys, with an optional offset per member (x[a] = x[root] + offset)."""

from __future__ import annotations


class UnionFind:
    """Keys are strings; offsets let an equality carry a fixed distance."""

    def __init__(self) -> None:
        self.parent: dict[str, str] = {}
        self.offset: dict[str, int] = {}
        self.size: dict[str, int] = {}

    def _seen(self, key: str) -> None:
        if key not in self.parent:
            self.parent[key] = key
            self.offset[key] = 0
            self.size[key] = 1

    def find(self, key: str) -> tuple[str, int]:
        """The root of key and key's offset from it, with path halving (no recursion)."""
        self._seen(key)
        root = self._halve(key)
        total = 0
        node = key
        while node != root:
            total += self.offset[node]
            node = self.parent[node]
        return root, total

    def _halve(self, key: str) -> str:
        """Walk to the root, pointing each visited key at its grandparent; returns the root."""
        node = key
        while self.parent[node] != node:
            mid = self.parent[node]
            top = self.parent[mid]
            if top != mid:
                self.offset[node] += self.offset[mid]
                self.parent[node] = top
            node = self.parent[node]
        return node

    def union(self, a: str, b: str, distance: int = 0) -> bool:
        """Make x[b] = x[a] + distance; False when a and b already disagree about it."""
        ra, oa = self.find(a)
        rb, ob = self.find(b)
        if ra == rb:
            return ob - oa == distance
        delta = oa + distance - ob
        if self.size[ra] >= self.size[rb]:
            self._attach(rb, ra, delta)
        else:
            self._attach(ra, rb, -delta)
        return True

    def _attach(self, child: str, root: str, delta: int) -> None:
        """Hang the root `child` under `root`, so that x[child] = x[root] + delta."""
        self.parent[child] = root
        self.offset[child] = delta
        self.size[root] += self.size[child]

    def same(self, a: str, b: str) -> bool:
        """True when a and b are in one class."""
        return self.find(a)[0] == self.find(b)[0]
