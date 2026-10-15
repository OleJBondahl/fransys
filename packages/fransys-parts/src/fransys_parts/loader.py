"""Load a part library into a Draft.

`load_path` runs `lint` first and raises `PartLibraryError` if it finds an `ERROR`; from
then on every field lint checked is trusted, so the record-building code below is
straight-line: no second, weaker validation happens here.
"""

import sys
from contextlib import contextmanager
from decimal import Decimal
from importlib.resources import as_file, files
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

from fransys_model.kernel import Draft, Finding, Id, ModelError, Origin, Severity, make_id
from fransys_model.vocab import (
    CableProductFacet,
    CorePair,
    FootprintFacet,
    OperatedBy,
    Part,
    PartCategory,
    PartLibrary,
    PcbFacet,
    SupplyFacet,
)

from . import _ratings, _toml
from ._function_build import _build_function, _PartContext
from .lint import SUPPORTED_SCHEMAS, lint

__all__ = ["SUPPORTED_SCHEMAS", "PartLibraryError", "library_root", "load", "load_path"]


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


def _loaded_libraries() -> list[str]:
    """The imported top-level packages that hold a `library.toml`, sorted."""
    found = []
    for name, module in sorted(sys.modules.items()):
        paths = getattr(module, "__path__", None)
        if "." not in name and paths and any((Path(p) / "library.toml").is_file() for p in paths):
            found.append(name)
    return found


@contextmanager
def library_root(package: str) -> Generator[Path]:
    """The folder of the part library in the installed data package `package`.

    Raises `ModuleNotFoundError` that names `package` and the part libraries already imported.
    """
    try:
        cm = as_file(files(package))
    except ModuleNotFoundError as error:
        loaded = ", ".join(_loaded_libraries()) or "none"
        msg = (
            f"no part library {package!r} is installed "
            f"(import name, as in fr.design({package!r})); "
            f"part libraries loaded in this process: {loaded}"
        )
        raise ModuleNotFoundError(msg, name=package) from error
    with cm as root:
        yield root


def load(package: str) -> Draft:
    """Load the part library shipped by an installed data package.

    Args:
        package: Import name of the data package, for example ``"demo_parts"``.

    Returns:
        A Draft holding the library's part, template, link and facet records. Every record's
        origin names the part file and line it came from.
    """
    with library_root(package) as root:
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
            operated_by=OperatedBy(part_data["operated_by"])
            if "operated_by" in part_data
            else None,
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
                pairs=tuple(
                    CorePair(cores=tuple(pair["cores"]), screen=pair.get("screen"))
                    for pair in cable_product.get("pairs", ())
                ),
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
