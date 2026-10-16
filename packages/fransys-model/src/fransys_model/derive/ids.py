"""Id aliases: an output annotates `UnitId`, not the record class `Id[Unit]` names."""

from fransys_model.kernel import Id
from fransys_model.layout import Page
from fransys_model.vocab import (
    AspectNode,
    Conductor,
    Document,
    Function,
    Item,
    Net,
    Port,
    Unit,
    UnitRelease,
)

type UnitId = Id[Unit]
type ItemId = Id[Item]
type FunctionId = Id[Function]
type PortId = Id[Port]
type DocumentId = Id[Document]
type NetId = Id[Net]
type ConductorId = Id[Conductor]
type AspectNodeId = Id[AspectNode]
type UnitReleaseId = Id[UnitRelease]
type PageId = Id[Page]
