"""`pipeline._svgs` memoises on the model AND its drawings, so test order cannot change a result.

Bug: the memo keyed on `model.digest` alone. A `BuildResult(model=m, findings=())` with no
drawings, drawn first, left an empty drawing for `m`; a later result of the same model with its
real drawings read it back and `check` raised `DOCUMENT_NO_DRAWINGS` (decision doc-order).
"""

from fransys import pipeline
from fransys.pipeline import BuildResult


def test_same_model_with_other_drawings_is_not_served_the_earlier_drawing(demo_cabinet_result):
    model = demo_cabinet_result.model
    real = demo_cabinet_result.drawings
    assert real  # examined: the cabinet really has drawn pages
    pipeline._svgs_cache.cache_clear()
    pipeline._result_svgs(BuildResult(model=model, findings=()))
    after = pipeline._svgs(model, real)
    pipeline._svgs_cache.cache_clear()
    assert after == pipeline._svgs(model, real)
    assert after.keys() >= {f"{page.kind}:{page.value}" for page in real}
