"""The page's lens data is `derive.signal_lens`, by table index (OVERVIEW O8, A4).

Breaks if a module's designation, a channel's number, kind or field device differs from
`signal_lens`, if their order changes, or if a spare channel gains a device. The plant is the
model package's cabinet use case, which has PLC modules with several signal kinds.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

from fransys_overview import html

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "packages/fransys-model/tests/usecases")
)
from cabinet import build_cabinet  # ty: ignore[unresolved-import] -- the use case folder is put on sys.path above

from fransys_layout.engines.overview import lay_out_overview
from fransys_model.derive import signal_lens
from fransys_model.kernel import freeze


def _page_lens(model: Any) -> list[dict[str, Any]]:
    text = html(lay_out_overview(model)[0])
    found = re.search(r'id="overview-data">(.*?)</script>', text, re.DOTALL)
    assert found is not None
    return json.loads(found.group(1))["lens"]


def test_the_page_lens_is_the_derived_lens() -> None:
    """A4: breaks if module, channel number, kind or device text differs from `signal_lens`."""
    model = freeze(build_cabinet())
    want = signal_lens(model)
    page = _page_lens(model)
    assert want
    assert [m["designation"] for m in page] == [m.designation for m in want]
    for got, module in zip(page, want, strict=True):
        assert [c["number"] for c in got["channels"]] == [c.number for c in module.channels]
        assert [c["kind"] for c in got["channels"]] == [c.kind.value for c in module.channels]
        assert [c["signal"] for c in got["channels"]] == [c.signal_name for c in module.channels]
        assert [c["device"] for c in got["channels"]] == [
            c.device_designation for c in module.channels
        ]


def test_the_lens_covers_digital_and_analogue_and_holds_no_id() -> None:
    """Breaks if a kind is dropped, a device loses its name or index, or an Id reaches the page."""
    page = _page_lens(freeze(build_cabinet()))
    channels = [c for m in page for c in m["channels"]]
    kinds = {c["kind"] for c in channels}
    assert any(k.startswith("digital") for k in kinds)
    assert any(k.startswith("analogue") for k in kinds)
    assert all((c["device"] is None) == (c["device_item"] is None) for c in channels)
    assert all(isinstance(m["item"], int | None) for m in page)
    assert all(isinstance(c["device_item"], int | None) for c in channels)
