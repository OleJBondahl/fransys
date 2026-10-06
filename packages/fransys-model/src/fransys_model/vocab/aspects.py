"""Vocabulary: IEC 81346 aspect structure (design/vocabulary.md 6 "Structure")."""

from fransys_model.kernel import AuthoringKey, Id, Value, record

from .core import Item
from .enums import Aspect


@record(kind="aspect_node")
class AspectNode:
    """A node in one IEC 81346 aspect tree.

    Example: `+C1` is a `LOCATION` node with `label="C1"`; a `PRODUCT` tree node
    `-K1` groups the relay example under an enclosure. Guarded by
    `validators.structure` (`ASPECT_CYCLE`, `ASPECT_CROSS_PARENT`).
    """

    id: Id[AspectNode]
    key: AuthoringKey
    aspect: Aspect
    parent: Id[AspectNode] | None
    label: str
    description: str
    ext: frozendict[str, Value] = frozendict()


@record(kind="placement")
class Placement:
    """An item occupying an aspect node; at most one per item per aspect.

    Example: the relay example's `Item` is placed at product node `-K1` and location
    node `+C1` (two `Placement`s, different aspects). Guarded by
    `validators.structure` (`PLACEMENT_DUPLICATE`).
    """

    id: Id[Placement]
    key: AuthoringKey
    item: Id[Item]
    node: Id[AspectNode]
    ext: frozendict[str, Value] = frozendict()
