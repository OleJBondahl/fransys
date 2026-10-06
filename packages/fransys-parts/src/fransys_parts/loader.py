"""Load a part library into a Draft (spec section 7, rulings P2, P5, P7).

`load_path` runs `lint` first and raises `PartLibraryError` if it finds an `ERROR`; from
then on every field lint checked is trusted, so the record-building code below is
straight-line: no second, weaker validation happens here (P5).
"""

from dataclasses import dataclass
from decimal import Decimal
from importlib.resources import as_file, files
from pathlib import Path

from fransys_model.kernel import Draft, Finding, Id, ModelError, Origin, Severity, make_id
from fransys_model.layout import SymbolChoice
from fransys_model.vocab import (
    CableProductFacet,
    ConnectorFacet,
    Energy,
    FootprintFacet,
    FunctionKind,
    FunctionTemplate,
    Gender,
    InternalLink,
    LinkKind,
    LinkRest,
    Part,
    PartCategory,
    PartLibrary,
    PcbFacet,
    PlcChannelFacet,
    PortRole,
    PortTemplate,
    ProtectionType,
    SignalType,
    SupplyFacet,
)

from . import _pole_facts, _ratings, _toml
from .lint import SUPPORTED_SCHEMAS, lint

__all__ = ["SUPPORTED_SCHEMAS", "PartLibraryError", "load", "load_path"]


@dataclass(frozen=True, slots=True)
class _PartContext:
    """A part's authoring key and id, threaded into its function builder."""

    key: tuple[str, ...]
    id: Id[Part]


class PartLibraryError(ModelError):
    """A part library failed `lint`; `findings` holds every finding of that run.

    Warnings included, not only the `ERROR`s that triggered the raise: a caller
    fixing the library wants the whole report, not a partial one.
    """

    def __init__(self, findings: tuple[Finding, ...]) -> None:
        """Store every finding `lint` returned, in its own order."""
        errors = sum(1 for f in findings if f.severity is Severity.ERROR)
        super().__init__(f"{errors} error(s) in the part library")
        self.findings = findings


def load(package: str) -> Draft:
    """Load the part library shipped by an installed data package.

    Args:
        package: Import name of the data package, for example ``"demo_parts"``.

    Returns:
        A Draft holding the library's part, template, link and facet records. Every record's
        origin names the part file and line it came from.
    """
    with as_file(files(package)) as root:
        return load_path(root)


def load_path(root: Path) -> Draft:
    """Load the part library in the directory `root` (the directory holding ``library.toml``).

    Returns:
        The same Draft `load` gives for an installed package.

    Raises:
        PartLibraryError: `lint(root)` found an `ERROR`. Nothing is built.
    """
    root = Path(root)
    findings = lint(root)
    if any(f.severity is Severity.ERROR for f in findings):
        raise PartLibraryError(findings)

    draft = Draft()
    library_parsed = _toml.parse(root / "library.toml", relative_to=root)
    # `errors` is empty, so lint already ruled out TOML_INVALID: `.data` parsed clean.
    library_data = library_parsed.data
    if library_data is None:
        return draft
    library_key = ("part_library", library_data["name"])
    library_id = make_id(PartLibrary, library_key)
    draft.add(
        PartLibrary(
            id=library_id,
            key=library_key,
            name=library_data["name"],
            version=library_data["version"],
        ),
        origin=Origin(file=library_parsed.path, line=1, note=""),
    )

    parts_dir = root / "parts"
    part_files = sorted(parts_dir.glob("*.toml")) if parts_dir.is_dir() else ()
    for file_path in part_files:
        _build_part_file(draft, _toml.parse(file_path, relative_to=root), library_id)
    return draft


def _build_part_file(draft: Draft, parsed: _toml.ParsedFile, library_id: Id[PartLibrary]) -> None:
    # `load_path` only reaches here after `lint` found no ERROR, so `.data` parsed clean.
    data = parsed.data
    if data is None:
        return
    origins = parsed.origins
    part_data = data["part"]
    part_key = ("part", part_data["manufacturer"], part_data["mpn"])
    part = _PartContext(key=part_key, id=make_id(Part, part_key))
    part_origin = Origin(file=parsed.path, line=origins.get(("part",), 1), note="")
    draft.add(
        Part(
            id=part.id,
            key=part_key,
            mpn=part_data["mpn"],
            manufacturer=part_data["manufacturer"],
            description=part_data["description"],
            category=PartCategory(part_data["category"]),
            class_code=part_data["class_code"],
            library=library_id,
        ),
        origin=part_origin,
    )

    for index, entry in enumerate(data.get("function", ())):
        _build_function(draft, entry, index, part, parsed)

    for index, supply in enumerate(data.get("supply", ())):
        origin = Origin(file=parsed.path, line=origins.get(("supply", index), 1), note="")
        key = (*part_key, "supply", supply["supplier"], supply["supplier_part_number"])
        draft.add(
            SupplyFacet(
                id=make_id(SupplyFacet, key),
                key=key,
                subject=part.id,
                supplier=supply["supplier"],
                supplier_part_number=supply["supplier_part_number"],
                note=supply.get("note", ""),
            ),
            origin=origin,
        )

    if "footprint" in data:
        origin = Origin(file=parsed.path, line=origins.get(("footprint",), 1), note="")
        footprint = data["footprint"]
        key = (*part_key, "footprint")
        draft.add(
            FootprintFacet(
                id=make_id(FootprintFacet, key),
                key=key,
                subject=part.id,
                library=footprint["library"],
                name=footprint["name"],
            ),
            origin=origin,
        )

    if "cable_product" in data:
        origin = Origin(file=parsed.path, line=origins.get(("cable_product",), 1), note="")
        cable_product = data["cable_product"]
        key = (*part_key, "cable_product")
        draft.add(
            CableProductFacet(
                id=make_id(CableProductFacet, key),
                key=key,
                subject=part.id,
                core_colours=tuple(cable_product["core_colours"]),
                gauge_mm2=Decimal(cable_product["gauge_mm2"]),
                shielded=cable_product["shielded"],
            ),
            origin=origin,
        )

    if "pcb" in data:
        origin = Origin(file=parsed.path, line=origins.get(("pcb",), 1), note="")
        pcb = data["pcb"]
        key = (*part_key, "pcb")
        draft.add(
            PcbFacet(id=make_id(PcbFacet, key), key=key, subject=part.id, revision=pcb["revision"]),
            origin=origin,
        )

    if "rating" in data:
        rating_line = origins.get(("rating",), 1)
        rating_origin = Origin(file=parsed.path, line=rating_line, note="")
        _ratings.add_part_rating(draft, data["rating"], part.id, part_key, rating_origin)


def _protection_type(entry: _toml.Table) -> ProtectionType | None:
    table = entry.get("protection")
    return ProtectionType(table["type"]) if type(table) is dict and "type" in table else None


def _build_function(
    draft: Draft, entry: _toml.Table, index: int, part: _PartContext, parsed: _toml.ParsedFile
) -> None:
    origins = parsed.origins
    origin = Origin(file=parsed.path, line=origins.get(("function", index), 1), note="")
    name = entry["name"]
    function_key = (*part.key, "function", name)
    function_id = make_id(FunctionTemplate, function_key)
    draft.add(
        FunctionTemplate(
            id=function_id,
            key=function_key,
            part=part.id,
            name=name,
            kind=FunctionKind(entry["kind"]),
            protection_type=_protection_type(entry),
            energy=Energy(entry["energy"]) if "energy" in entry else None,
        ),
        origin=origin,
    )

    port_ids = {}
    for port in entry["ports"]:
        pole_side, conductor_mark = _pole_facts.facts(entry, port)
        port_key = (*function_key, "port", port["name"])
        port_id = make_id(PortTemplate, port_key)
        port_ids[port["name"]] = port_id
        draft.add(
            PortTemplate(
                id=port_id,
                key=port_key,
                function=function_id,
                name=port["name"],
                role=PortRole(port["role"]),
                # model-0053 (F2): the part's own pin marking, when it differs from the name
                marking=port.get("marking"),
                pole_side=pole_side,
                conductor_mark=conductor_mark,
            ),
            origin=origin,
        )

    for link in entry.get("links", ()):
        link_key = (*function_key, "link", link["a"], link["b"])
        draft.add(
            InternalLink(
                id=make_id(InternalLink, link_key),
                key=link_key,
                a=port_ids[link["a"]],
                b=port_ids[link["b"]],
                kind=LinkKind(link["kind"]),
                rest=LinkRest(link["rest"]) if "rest" in link else None,
            ),
            origin=origin,
        )

    symbol = entry.get("symbol")
    if symbol is not None:
        port_map = {
            port["name"]: port["symbol_port"]
            for port in entry["ports"]
            if "symbol_port" in port and port["symbol_port"] != port["name"]
        }
        choice_key = (*function_key, "symbol_choice")
        draft.add(
            SymbolChoice(
                id=make_id(SymbolChoice, choice_key),
                key=choice_key,
                function=None,
                template=function_id,
                part=None,
                kind=None,
                symbol=symbol,
                port_map=frozendict(port_map),
            ),
            origin=origin,
        )

    connector = entry.get("connector")
    if connector is not None:
        key = (*function_key, "connector")
        connector_line = origins.get(("function", index, "connector"), origin.line)
        draft.add(
            ConnectorFacet(
                id=make_id(ConnectorFacet, key),
                key=key,
                subject=function_id,
                style=connector["style"],
                pincount=connector["pincount"],
                gender=Gender(connector["gender"]) if "gender" in connector else None,
                marking=connector.get("marking"),
            ),
            origin=Origin(file=parsed.path, line=connector_line, note=""),
        )

    plc_channel = entry.get("plc_channel")
    if plc_channel is not None:
        key = (*function_key, "plc_channel")
        plc_channel_line = origins.get(("function", index, "plc_channel"), origin.line)
        draft.add(
            PlcChannelFacet(
                id=make_id(PlcChannelFacet, key),
                key=key,
                subject=function_id,
                signal=SignalType(plc_channel["signal"]),
                channel=plc_channel["channel"],
            ),
            origin=Origin(file=parsed.path, line=plc_channel_line, note=""),
        )

    table_origins = {
        table: Origin(
            file=parsed.path, line=origins.get(("function", index, table), origin.line), note=""
        )
        for table in ("rating", "operating")
    }
    _ratings.add_function_tables(draft, entry, function_id, function_key, table_origins)
