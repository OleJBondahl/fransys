"""What a marker row is measured against (S20): the wiring that sets its lanes, sheet and costs."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fransys_layout.stages.stacking import JoinedRun
    from fransys_layout.stages.types import Column, Connection, Profile, SheetFormat

    from .stand import Wired


@dataclass(frozen=True, slots=True)
class MarkerRoom:
    """The wiring a marker row reads (columns, connections, runs, wired ports), sheet and costs."""

    columns: tuple[Column, ...]
    connections: tuple[Connection, ...]
    joins: tuple[JoinedRun, ...]
    wired: Wired
    sheet: SheetFormat
    profile: Profile
