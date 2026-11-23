"""The `Cable` handle: its cores and open cores, split from `handles.py`."""

from dataclasses import dataclass

from fransys_model.derive import cores_past_product
from fransys_model.kernel import AuthoringKey, Id, make_id
from fransys_model.vocab import Conductor, ConductorKind, CoreFacet, OpenCoreFacet
from fransys_model.vocab import Item as ModelItem

from ._keys import scoped
from ._origin import caller_origin
from .errors import AuthorError
from .handles import Port, _Recorder, as_port


@dataclass(slots=True)
class Cable:
    """A cable item: `d.cable(mpn, ...)`, then `cable.core(index, a, b)`."""

    _recorder: _Recorder
    id: Id[ModelItem]
    key: AuthoringKey
    _core_colours: tuple[str, ...]

    def core(self, index: int, a: Port, b: Port) -> None:
        """Core `index` of this cable, between `a` and `b`; its colour is the part's.

        Raises `AuthorError` when `index` is not one of this cable's cores.
        """
        if cores_past_product(len(self._core_colours), index):
            msg = f"core {index} is out of range: this cable has {len(self._core_colours)} core(s)"
            raise AuthorError(msg)
        a, b = as_port(a), as_port(b)
        key = scoped(self.key, "core", str(index))
        conductor = Conductor(
            id=make_id(Conductor, key),
            key=key,
            a=a.id,
            b=b.id,
            kind=ConductorKind.CORE,
            carrier=self.id,
        )
        origin = caller_origin()
        self._recorder._add(conductor, origin)
        facet_key = scoped(key, "facet")
        facet = CoreFacet(
            id=make_id(CoreFacet, facet_key),
            key=facet_key,
            subject=conductor.id,
            index=index,
        )
        self._recorder._add(facet, origin)

    def open_core(self, index: int, at: Port | None = None) -> None:
        """Core `index` of this cable with one end or none: a spare, or a screen earthed at `at`.

        Raises `AuthorError` when `index` is not one of this cable's cores.
        """
        if cores_past_product(len(self._core_colours), index):
            msg = f"core {index} is out of range: this cable has {len(self._core_colours)} core(s)"
            raise AuthorError(msg)
        key = scoped(self.key, "open_core", str(index))
        facet = OpenCoreFacet(
            id=make_id(OpenCoreFacet, key),
            key=key,
            subject=self.id,
            index=index,
            at=None if at is None else as_port(at).id,
        )
        self._recorder._add(facet, caller_origin())
