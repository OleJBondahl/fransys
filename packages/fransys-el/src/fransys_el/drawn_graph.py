"""Union-find over any hashable keys, for the drawn netlist (DRAWN-NETLIST, el-0052)."""

__all__ = ["Union"]


class Union:
    """Union-find over any hashable keys."""

    def __init__(self) -> None:
        self._up: dict[object, object] = {}

    def find(self, key: object) -> object:
        """The root of `key`'s set."""
        self._up.setdefault(key, key)
        while self._up[key] != key:
            self._up[key] = self._up[self._up[key]]
            key = self._up[key]
        return key

    def join(self, a: object, b: object) -> None:
        """Put `a` and `b` in one set."""
        self._up[self.find(a)] = self.find(b)
