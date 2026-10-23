"""Field case: a contact table prints over no other text (CONTACT-TABLE; known gap, R284).

The engineering shape: the demo skid, whose sixteen valve relays sit behind one breaker and
whose contacts read back into a digital input module.
The bug: on the relay page the contact tables overprint each other and their coils (K8, K12,
K14, K16, K18, DO10): about 190 glyph pairs of different text overlap on that page, where every
other page has at most one pair of kerning noise.
The rule (CONTACT-TABLE): one text-sized table, never overlapping. Decision: owner 2026-10-19,
shipped as a known gap in the 0.21.0 release note; listed in tests/gap_flip_other.toml.
"""

import importlib.util
import tempfile
from functools import cache
from pathlib import Path

import fransys as fr
import pypdfium2 as pdfium
from _tables_on import TABLES_ON

_SKID = Path(__file__).parents[2] / "examples" / "demo-skid" / "skid.py"
_NOISE = 5  # overlapping glyph pairs a page may hold from kerning alone


@cache
def _pdf() -> bytes:
    spec = importlib.util.spec_from_file_location("skid", _SKID)
    assert spec is not None, f"cannot load {_SKID}"
    assert spec.loader is not None, f"no loader for {_SKID}"
    skid = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(skid)
    design, document = skid.design()
    paths = fr.write(
        fr.build(fr.parts("demo_parts"), design, document, settings=TABLES_ON),
        Path(tempfile.mkdtemp()),
    )
    return next(p for p in paths if p.suffix == ".pdf").read_bytes()


def _overlaps(page) -> int:
    text = page.get_textpage()
    boxes = [
        text.get_charbox(i) for i in range(text.count_chars()) if text.get_text_range(i, 1).strip()
    ]
    count = 0
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            wide = min(a[2], b[2]) - max(a[0], b[0])
            high = min(a[3], b[3]) - max(a[1], b[1])
            count += wide > 0.5 and high > 1.0
    return count


def test_no_page_has_overlapping_text():
    counts = [_overlaps(page) for page in pdfium.PdfDocument(_pdf())]
    assert max(counts) <= _NOISE, counts
