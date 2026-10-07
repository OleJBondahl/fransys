"""The functions every part declares, with their effective ratings (decision model-0165)."""

from fransys_model.vocab.rating_readers import part_rating, template_rating
from fransys_model.vocab.ratings import effective_rating
from fransys_model.vocab.tables import function_templates, parts
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.templates import FunctionTemplate, Part

from .rows import PartFunctionRow


def part_function_rows(model: Model) -> tuple[PartFunctionRow, ...]:
    """One row per function template of each part, a part with none gets one row; sorted.

    Reads the parts a model holds, built or not: no item is needed. The rating is
    `effective_rating`, the one fallback rule: the template's, else the part's.
    """
    by_part: dict[Id[Part], list[FunctionTemplate]] = {part: [] for part in parts(model)}
    for template in function_templates(model).values():
        by_part[template.part].append(template)
    rows = []
    for part_id, part in parts(model).items():
        own = part_rating(model, part_id)
        templates = sorted(by_part[part_id], key=lambda t: t.name)
        if not templates:
            rows.append(
                PartFunctionRow(
                    part=part_id, mpn=part.mpn, template=None, name="", kind=None, rating=own
                )
            )
        rows.extend(
            PartFunctionRow(
                part=part_id,
                mpn=part.mpn,
                template=t.id,
                name=t.name,
                kind=t.kind,
                rating=effective_rating(template_rating(model, t.id), own),
            )
            for t in templates
        )
    return tuple(sorted(rows, key=lambda r: (r.mpn, r.part, r.name)))
