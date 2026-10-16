"""Baseline listing, change list and numbering-pin row shapes (`derive.baseline`).

Row shapes beside `rows.py` (model-0199); they import nothing from it.
"""

from fransys_model.kernel import AuthoringKey, value
from fransys_model.vocab.ratings import Operating, Rating

from .release_order import ReleaseOrder, release_order
from .rows_removed import RemovedAncestry


@value
class BaselineUnit:
    """The `unit` key of a baseline listing: the listed unit's own release facts."""

    name: str
    version: int
    revision: int
    interface: str


@value
class BaselineItem:
    """One `items` entry of a baseline listing; `parent` is its parent's designation (0212)."""

    designation: str
    mpn: str
    manufacturer: str
    installed: bool
    external: bool
    position: int | None
    parent: str | None = None


@value
class BaselineNestedUnit(BaselineUnit):
    """One `units` entry: a unit release directly nested in the listed unit, with its instances.

    `instances` names each instance sharing this `(name, version, revision)` release: the
    smallest, in sort order, of its own root items' unit designations in the listed unit.
    """

    instances: tuple[str, ...]


@value
class BaselineBoundary:
    """One `boundary` entry: a boundary function of the listed unit, with its stated rating."""

    designation: str
    ports: tuple[str, ...]
    rating: Rating | None
    operating: Operating | None


@value
class BaselineConductor:
    """One `conductors` entry: a conductor belonging to the listed unit."""

    kind: str
    a: str
    b: str
    carrier: str | None
    colour: str | None
    gauge_mm2: str | None
    length_mm: int | None
    label: str | None


@value
class BaselineMate:
    """One `mates` entry: a `Mate` with a side on an item of the listed unit itself."""

    a: str
    b: str


@value
class BaselineNet:
    """One `nets` entry: a `Net` with a member port on an item of the listed unit itself."""

    name: str | None
    net_class: str
    potential: str | None
    ports: tuple[str, ...]


@value
class Listing:
    """A unit's baseline listing: designation-relative, format-versioned."""

    unit: BaselineUnit
    items: tuple[BaselineItem, ...]
    units: tuple[BaselineNestedUnit, ...]
    boundary: tuple[BaselineBoundary, ...]
    conductors: tuple[BaselineConductor, ...]
    mates: tuple[BaselineMate, ...]
    nets: tuple[BaselineNet, ...]


@value
class Change:
    """One difference between two listings of the same unit (`derive.baseline.diff`).

    `subject` is the CSV-ready identity text (`Change`'s own `field`/`before`/`after` are
    always plain `str`, never a bare int or bool — the value already rendered). `parts` is the
    identity's own rendered pieces with NO backticks and NO joining, for a renderer that needs
    "between `a` and `b`" or "`instance` (name)" shapes without ever parsing `subject` (reports
    package rule: never parse a designation). `detail` is a short rendered description for an
    `added`/`removed` row that needs more than its bare identity to be legible (populated only
    for `items` and `boundary`, per the worked example -- every other section's
    `added`/`removed` rows carry `detail=""`; `changed` rows always carry `detail=""` too, since
    `field`/`before`/`after` already say what changed).
    """

    section: str
    change: str
    subject: str
    field: str
    before: str
    after: str
    parts: tuple[str, ...]
    detail: str


@value
class ListingDiff:
    """The change list from listing `a` to listing `b` (`derive.baseline.diff`)."""

    a: BaselineUnit
    b: BaselineUnit
    changes: tuple[Change, ...]
    ancestry: tuple[RemovedAncestry, ...] = ()


CHANGE_COLUMNS = ("section", "change", "subject", "field", "before", "after")


@value
class NumberingItem:
    """One `items` entry of a unit's numbering pins: an item that prints a designation.

    `key` is `derive.unit_relative_key`'s. `scope` is the relative key of the board or
    harness the item's designation reads through, `None` for none. `code` is the item's
    part's `class_code`, or `None` for a part-less item -- one record, one spelling of
    absence, matching `scope`'s own `None` (ruling 2026-09-27); `code` never gates
    reuse, a reserved text is taken by its `text` alone in its group. `text` is the
    item's OWN label (`derive.designation.own_designation_or_none`), never the full
    `item_designation` chain -- the release check compares on this field, not the
    chain. `authored` says whether the engineer wrote it (a tag) or the pass assigned it.
    """

    key: AuthoringKey
    scope: AuthoringKey | None
    code: str | None
    text: str
    authored: bool


@value
class NumberingRetired:
    """One `retired` entry: a designation given out earlier in this version.

    Its item is gone, or has moved to a different group or class code. `code` is `None` for
    a part-less item, the same spelling `NumberingItem.code` uses.
    """

    scope: AuthoringKey | None
    code: str | None
    text: str


@value
class NumberingPins:
    """A unit's numbering pins at release: `baseline/numbering.json`'s own shape."""

    items: tuple[NumberingItem, ...]
    retired: tuple[NumberingRetired, ...]


@value
class ChangeSection:
    """One printed section of a change note: its name and its rows grouped by subject.

    `groups` are runs of consecutive `Change` rows with one `subject` (`derive.change_sections`).
    """

    section: str
    groups: tuple[tuple[Change, ...], ...]


@value
class ReleaseIdentity:
    """A release's identity (model-0280): name, version, revision, interface."""

    name: str
    version: int
    revision: int
    interface: str


@value
class StoredRelease:
    """One stored release folder, as the facade reads it (model-0267; pattern of `ListingDiff`).

    `folder` is the `<version>.<revision>` folder name, `listing` its `baseline/listing.json` and
    `numbering` its `baseline/numbering.json` (`None` when it has none). `identity` and `order`
    read off the listing's own unit. The manifest joins when a second reader needs its keys.
    """

    folder: str
    listing: Listing
    numbering: NumberingPins | None

    @property
    def identity(self) -> ReleaseIdentity:
        """The listed unit's name, version, revision and interface."""
        unit = self.listing.unit
        return ReleaseIdentity(
            name=unit.name, version=unit.version, revision=unit.revision, interface=unit.interface
        )

    @property
    def order(self) -> ReleaseOrder:
        """The folder's `release_order` key, from its listing."""
        identity = self.identity
        return release_order(identity.version, identity.revision)


@value
class StoredReleases:
    """Every stored release below `<into>/<name>/` that has a listing, in folder order."""

    releases: tuple[StoredRelease, ...]


@value
class ManifestHistory:
    """The `history` entry of a manifest: the release's current revision entry."""

    date: str
    text: str
    created: str
    checked: str
    approved: str


@value
class ManifestLibrary:
    """One `part_libraries` entry of a manifest: a part library name and version in use."""

    name: str
    version: str


@value
class ManifestNested:
    """One `nested` entry of a manifest: a nested release with its listing's sha256 hex digest."""

    name: str
    version: int
    revision: int
    listing_digest: str


@value
class ManifestRows:
    """The manifest facts that come from the model and print no designation (model-0267).

    `identity` is the release's; `entry` its current revision entry (the manifest's
    `history`), `None` when it has none; `part_libraries` and `nested` come sorted.
    """

    identity: ReleaseIdentity
    entry: ManifestHistory | None
    part_libraries: tuple[ManifestLibrary, ...]
    nested: tuple[ManifestNested, ...]
