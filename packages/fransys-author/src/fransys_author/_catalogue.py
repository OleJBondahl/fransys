"""The part catalogue read from `parts` once (spec A1, A-r1); A5's checks run in `find()`."""

import difflib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.vocab import (
    CableProductFacet,
    FunctionTemplate,
    InternalLink,
    OperatingFacet,
    Part,
    PartBundle,
    PartRatingFacet,
    PortTemplate,
    RatingFacet,
    effective_rating,
)

from .errors import AuthorError

if TYPE_CHECKING:
    from fransys_model.kernel import Draft, Id
    from fransys_model.vocab import Operating, Rating


@dataclass(frozen=True, slots=True)
class Catalogue:
    """The `parts` Draft, indexed for lookup by MPN and for stamping a `PartBundle`."""

    by_manufacturer_mpn: dict[tuple[str, str], Part]
    by_mpn: dict[str, tuple[Part, ...]]
    function_templates: dict[Id[Part], tuple[FunctionTemplate, ...]]
    port_templates: dict[Id[FunctionTemplate], tuple[PortTemplate, ...]]
    internal_links: dict[Id[Part], tuple[InternalLink, ...]]
    cable_products: dict[Id[Part], CableProductFacet]
    template_ratings: dict[Id[FunctionTemplate], Rating]
    part_ratings: dict[Id[Part], Rating]
    operating_envelopes: dict[Id[FunctionTemplate], Operating]

    def find(self, mpn: str | tuple[str, str]) -> Part:
        """The `Part` named by a bare MPN or an explicit `(manufacturer, mpn)` (spec A5)."""
        if isinstance(mpn, tuple):
            manufacturer, number = mpn
            found = self.by_manufacturer_mpn.get((manufacturer, number))
            if found is None:
                msg = (
                    f"no part {number!r} from manufacturer {manufacturer!r} in the loaded libraries"
                )
                raise AuthorError(msg)
            return found
        matches = self.by_mpn.get(mpn, ())
        if not matches:
            raise AuthorError(_unknown_mpn_message(mpn, self.by_mpn))
        if len(matches) > 1:
            manufacturers = ", ".join(sorted(part.manufacturer for part in matches))
            msg = (
                f"MPN {mpn!r} is ambiguous across manufacturers ({manufacturers}); "
                f'write d.item(("<manufacturer>", {mpn!r}), ...)'
            )
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
        names = ", ".join(sorted(template.name for template in templates)) or "none"
        msg = (
            f"part {part.mpn!r} has no function named {function!r} "
            f"(a function is named by its str name); it has: {names}"
        )
        raise AuthorError(msg)

    def rating(self, part: Part, function: str | None) -> Rating | None:
        """The rating of `part`, or with `function` that function's (template, else part)."""
        part_rating = self.part_ratings.get(part.id)
        if function is None:
            return part_rating
        template = self.template_of(part, function)
        return effective_rating(self.template_ratings.get(template.id), part_rating)

    def operating(self, part: Part, function: str) -> Operating | None:
        """The operating envelope of the function template of `part` named `function`."""
        return self.operating_envelopes.get(self.template_of(part, function).id)

    def bundle(self, part: Part) -> PartBundle:
        """The `PartBundle` `instantiate()` needs to stamp one `Item` of `part`."""
        function_templates = self.function_templates.get(part.id, ())
        port_templates = tuple(
            template
            for function_template in function_templates
            for template in self.port_templates.get(function_template.id, ())
        )
        return PartBundle(
            part=part,
            function_templates=function_templates,
            port_templates=port_templates,
            internal_links=self.internal_links.get(part.id, ()),
        )


def build_catalogue(parts: Draft) -> Catalogue:
    """Index every `Part`, template, `InternalLink` and rating or operating facet of `parts`."""
    records = parts.records()
    by_manufacturer_mpn: dict[tuple[str, str], Part] = {}
    by_mpn: dict[str, list[Part]] = {}
    function_templates: dict[Id[Part], list[FunctionTemplate]] = {}
    port_templates: dict[Id[FunctionTemplate], list[PortTemplate]] = {}
    port_template_function: dict[Id[PortTemplate], Id[FunctionTemplate]] = {}
    function_template_part: dict[Id[FunctionTemplate], Id[Part]] = {}
    internal_links: dict[Id[Part], list[InternalLink]] = {}
    cable_products: dict[Id[Part], CableProductFacet] = {}
    template_ratings: dict[Id[FunctionTemplate], Rating] = {}
    part_ratings: dict[Id[Part], Rating] = {}
    operating_envelopes: dict[Id[FunctionTemplate], Operating] = {}
    for record in records:
        if isinstance(record, Part):
            by_manufacturer_mpn[record.manufacturer, record.mpn] = record
            by_mpn.setdefault(record.mpn, []).append(record)
        elif isinstance(record, FunctionTemplate):
            function_templates.setdefault(record.part, []).append(record)
            function_template_part[record.id] = record.part
        elif isinstance(record, PortTemplate):
            port_templates.setdefault(record.function, []).append(record)
            port_template_function[record.id] = record.function
        elif isinstance(record, CableProductFacet):
            cable_products[record.subject] = record
        else:
            _index_value(record, template_ratings, part_ratings, operating_envelopes)
    for record in records:
        if isinstance(record, InternalLink):
            # designer ruling 2026-09-27, S-A: direct index, no guard. A part file can never
            # produce a link whose port owns no function template (parts lint's
            # LINK_PORT_UNKNOWN rejects it at the source), so this must raise loudly, not
            # silently drop the link, if that impossible state ever arises.
            part_id = function_template_part[port_template_function[record.a]]
            internal_links.setdefault(part_id, []).append(record)
    return Catalogue(
        by_manufacturer_mpn=by_manufacturer_mpn,
        by_mpn={mpn: tuple(parts_) for mpn, parts_ in by_mpn.items()},
        function_templates={
            part: tuple(templates) for part, templates in function_templates.items()
        },
        port_templates={fn: tuple(templates) for fn, templates in port_templates.items()},
        internal_links={part: tuple(links) for part, links in internal_links.items()},
        cable_products=cable_products,
        template_ratings=template_ratings,
        part_ratings=part_ratings,
        operating_envelopes=operating_envelopes,
    )


def _index_value(
    record: object,
    template_ratings: dict[Id[FunctionTemplate], Rating],
    part_ratings: dict[Id[Part], Rating],
    operating_envelopes: dict[Id[FunctionTemplate], Operating],
) -> None:
    """File `record` under its subject when it is one of the three rating or operating facets."""
    if isinstance(record, RatingFacet):
        template_ratings[record.subject] = record.rating
    elif isinstance(record, PartRatingFacet):
        part_ratings[record.subject] = record.rating
    elif isinstance(record, OperatingFacet):
        operating_envelopes[record.subject] = record.operating


def _unknown_mpn_message(mpn: str, by_mpn: dict[str, tuple[Part, ...]]) -> str:
    close = difflib.get_close_matches(mpn, sorted(by_mpn), n=3)
    if not close:
        return f"no part with MPN {mpn!r} in the loaded libraries"
    return f"no part with MPN {mpn!r} in the loaded libraries; closest: {', '.join(close)}"
