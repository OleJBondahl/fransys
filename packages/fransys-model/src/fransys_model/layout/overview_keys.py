"""The authoring keys of the overview records: one home, read by the engine and by the page.

A view is keyed by its unit, level, mode and open thing; a box by its reference and, for a stub,
the box it hangs on; a line by its kind, carrier, strip and ends. Decision model-0198.
"""

from fransys_model.kernel import AuthoringKey, Id, render_id, value
lazy from fransys_model.vocab.core import Item, Unit

from .overview_ref import OverviewMode, OverviewRef

__all__ = ["BoxKey", "box_key", "line_key", "ref_token", "view_key"]


def ref_token(ref: OverviewRef) -> str:
    """A reference as text: its kind and its one id (`-` for none)."""
    held = ref.unit or ref.item or ref.node
    return f"{ref.kind.value}:{'-' if held is None else held.value}"


@value
class BoxKey:
    """The identity of a box in a view: what it stands for and, for a stub, the box it hangs on."""

    ref: OverviewRef
    at: OverviewRef | None = None

    @property
    def token(self) -> str:
        """The box as text: its reference, then `@` and the reference of the box it hangs on."""
        base = ref_token(self.ref)
        return base if self.at is None else f"{base}@{ref_token(self.at)}"


def view_key(
    unit: Id[Unit] | None,
    level: OverviewRef | None,
    mode: OverviewMode,
    open_: OverviewRef | None,
    open_at: OverviewRef | None = None,
) -> AuthoringKey:
    """The key of the `layout.overview_view` of one level in one mode with one box open."""
    owner = () if unit is None else ("unit", render_id(unit))
    leveled = () if level is None else ("level", ref_token(level))
    opened = () if open_ is None else ("open", BoxKey(ref=open_, at=open_at).token)
    return ("layout", "overview", "view", *owner, *leveled, "mode", mode.value, *opened)


def box_key(view: AuthoringKey, box: BoxKey) -> AuthoringKey:
    """The key of one box record of the view keyed `view`."""
    return (*view, "box", box.token)


def line_key(
    view: AuthoringKey,
    kind: str,
    ends: tuple[BoxKey, BoxKey],
    carried: tuple[Id[Item] | None, Id[Item] | None],
) -> AuthoringKey:
    """The key of one line record of the view keyed `view`; `carried` is its cable and its strip."""
    via, strip = carried
    a, b = ends
    carrier = "-" if via is None else render_id(via)
    through = "-" if strip is None else render_id(strip)
    return (*view, "line", kind, carrier, through, a.token, b.token)
