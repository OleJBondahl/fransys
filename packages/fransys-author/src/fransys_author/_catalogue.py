"""The part catalogue read from `parts` once; the checks run in `find()`."""

import difflib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fransys_model.kernel import natural_join
from fransys_model.vocab import (
    CableProductFacet,
    FunctionTemplate,
    InternalLink,
    OperatingFacet,
    Part,
    PartBundle,
    PortTemplate,
)

from .errors import AuthorError

if TYPE_CHECKING:
    from fransys_model.kernel import Draft, Id
    from fransys_model.vocab import Operating


@dataclass(frozen=True, slots=True)
class Catalogue:
    """The `parts` Draft, indexed for lookup by MPN and for stamping a `PartBundle`."""

    by_manufacturer_mpn: dict[tuple[str, str], Part]
    by_mpn: dict[str, tuple[Part, ...]]
    function_templates: dict[Id[Part], tuple[FunctionTemplate, ...]]
    port_templates: dict[Id[FunctionTemplate], tuple[PortTemplate, ...]]
    internal_links: dict[Id[Part], tuple[InternalLink, ...]]
    cable_products: dict[Id[Part], CableProductFacet]
    operating_envelopes: dict[Id[FunctionTemplate], Operating]

    def find(self, mpn: str | tuple[str, str]) -> Part:
        """The `Part` named by a bare MPN or an explicit `(manufacturer, mpn)`."""
        if isinstance(mpn, tuple):
            manufacturer, number = mpn
            found = self.by_manufacturer_mpn.get((manufacturer, number))
            if found is None:
                msg = f"no part {number!r} from manufacturer {manufacturer!r} in the loaded libraries"
                raise AuthorError(msg)
            return found
        matches = self.by_mpn.get(mpn, ())
        if not matches:
            raise AuthorError(_unknown_mpn_message(mpn, self.by_mpn))
        if len(matches) > 1:
            manufacturers = ", ".join(sorted(part.manufacturer for part in matches))
            msg = f'MPN {mpn!r} is ambiguous across manufacturers ({manufacturers}); write the part as ("<manufacturer>", {mpn!r})'
            raise AuthorError(msg)
        return matches[0]

    def cable_product(self, part: Part) -> CableProductFacet:
        """The `cable_product` facet of `part`; a part without one is not a cable."""
        found = self.cable_products.get(part.id)
        if found is None:
            msg = f"part {part.mpn!r} has no cable_product facet, so it is not a cable"
            raise AuthorError(msg)
        return found

    def template_of(self, part: Part, function: str) -> FunctionTemplate:
        """The function template of `part` named `function`; the error lists the names it has."""
        templates = self.function_templates.get(part.id, ())
        for template in templates:
            if template.name == function:
                return template
        names = natural_join(template.name for template in templates) or "none"
        msg = f"part {part.mpn!r} has no function named {function!r} (a function is named by its str name); it has: {names}"
        raise AuthorError(msg)

    def operating(self, part: Part, function: str) -> Operating | None:
        """The operating envelope of the function template of `part` named `function`."""
        return self.operating_envelopes.get(self.template_of(part, function).id)

    def bundle(self, part: Part) -> PartBundle:
        """The `PartBundle` `instantiate()` needs to stamp one `Item` of `part`."""
        function_templates = self.function_templates.get(part.id, ())
        port_templates = tuple(template for function_template in function_templates for template in self.port_templates.get(function_template.id, ()))
        return PartBundle(
            part=part,
            function_templates=function_templates,
            port_templates=port_templates,
            internal_links=self.internal_links.get(part.id, ()),
        )


@dataclass(slots=True)
class _Index:
    """The mutable indexes `build_catalogue` fills record by record."""

    by_manufacturer_mpn: dict[tuple[str, str], Part] = field(default_factory=dict)
    by_mpn: dict[str, list[Part]] = field(default_factory=dict)
    function_templates: dict[Id[Part], list[FunctionTemplate]] = field(default_factory=dict)
    port_templates: dict[Id[FunctionTemplate], list[PortTemplate]] = field(default_factory=dict)
    port_template_function: dict[Id[PortTemplate], Id[FunctionTemplate]] = field(default_factory=dict)
    function_template_part: dict[Id[FunctionTemplate], Id[Part]] = field(default_factory=dict)
    internal_links: dict[Id[Part], list[InternalLink]] = field(default_factory=dict)
    cable_products: dict[Id[Part], CableProductFacet] = field(default_factory=dict)
    operating_envelopes: dict[Id[FunctionTemplate], Operating] = field(default_factory=dict)

    def add(self, record: object) -> None:
        """File `record` under its subject."""
        if isinstance(record, Part):
            self.by_manufacturer_mpn[record.manufacturer, record.mpn] = record
            self.by_mpn.setdefault(record.mpn, []).append(record)
        elif isinstance(record, FunctionTemplate):
            self.function_templates.setdefault(record.part, []).append(record)
            self.function_template_part[record.id] = record.part
        elif isinstance(record, PortTemplate):
            self.port_templates.setdefault(record.function, []).append(record)
            self.port_template_function[record.id] = record.function
        elif isinstance(record, CableProductFacet):
            self.cable_products[record.subject] = record
        elif isinstance(record, OperatingFacet):
            self.operating_envelopes[record.subject] = record.operating

    def add_link(self, record: InternalLink) -> None:
        """File an internal link under the part that owns its port."""
        # ruling 2026-09-27, S-A: direct index, no guard. A part file can never
        # produce a link whose port owns no function template (parts lint's
        # LINK_PORT_UNKNOWN rejects it at the source), so this must raise loudly, not
        # silently drop the link, if that impossible state ever arises.
        part_id = self.function_template_part[self.port_template_function[record.a]]
        self.internal_links.setdefault(part_id, []).append(record)

    def catalogue(self) -> Catalogue:
        """The frozen `Catalogue` of what was filed."""
        return Catalogue(
            by_manufacturer_mpn=self.by_manufacturer_mpn,
            by_mpn={mpn: tuple(parts_) for mpn, parts_ in self.by_mpn.items()},
            function_templates={part: tuple(templates) for part, templates in self.function_templates.items()},
            port_templates={fn: tuple(templates) for fn, templates in self.port_templates.items()},
            internal_links={part: tuple(links) for part, links in self.internal_links.items()},
            cable_products=self.cable_products,
            operating_envelopes=self.operating_envelopes,
        )


def build_catalogue(parts: Draft) -> Catalogue:
    """Index every `Part`, template, `InternalLink` and operating facet of `parts`."""
    records = parts.records()
    index = _Index()
    for record in records:
        index.add(record)
    for record in records:
        if isinstance(record, InternalLink):
            index.add_link(record)
    return index.catalogue()


def _unknown_mpn_message(mpn: str, by_mpn: dict[str, tuple[Part, ...]]) -> str:
    close = difflib.get_close_matches(mpn, list(by_mpn), n=3)
    if not close:
        return f"no part with MPN {mpn!r} in the loaded libraries"
    return f"no part with MPN {mpn!r} in the loaded libraries; closest: {', '.join(close)}"
