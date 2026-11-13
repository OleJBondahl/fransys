"""Field case KI-768: an A3 unit, a 16-channel DI module, 6 contacts, 2 switches, 9 terminals of one strip, long contact pin labels.
The bug: the cut left a row of about 185 G on a page with 164 G of content (WIDER_THAN_PAGE); the widest unsplittable item is the module's box."""

from contextlib import nullcontext
from functools import cache
from pathlib import Path

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_model.kernel import id_namespace

DATA = Path(__file__).parent / "data"
SALTS = ("-", "a", "b", "c", "d", "e")
REFUSED = {"WIDER_THAN_PAGE", "PAGE_OVERFLOW"}
# Shapes: "" is 14-letter contact pins (KI-768); "-L" is 8-letter pins on every part (KI-972); "30" is "" with 30 contacts
# in series on channel 1, a truly tall column on the card (R2283).
SHAPES = {"": ("", "_", "_" + "W" * 14, 0), "-L": ("-L", "_" + "W" * 8, "_" + "W" * 8, 0), "30": ("", "_", "_" + "W" * 14, 30)}


@cache
def _built(shape: str, salt: str) -> fr.BuildResult:
    with pytest.MonkeyPatch.context() as mp, id_namespace(salt) if salt != "-" else nullcontext():
        mp.syspath_prepend(str(DATA))
        d = fr.design("wide_row_parts", place="CAB")
        cab = d.location("CAB", "Cabinet")
        wire = (BU, 0.5)
        sfx, ch, long, chain = SHAPES[shape]
        with d.function("DI", "Inputs"):
            card = d.device("K1", f"WIDE-DI-16P{sfx}")
        with d.function("F", "Feed"):
            strip = d.terminal_strip("X1", "WIDE-TB-2.5", 9)
            d.series(strip[8].inner, card.power["24V"], wire=wire)
            d.series(card.power["0V"], strip[9].inner, wire=wire)
            for n in range(1, 7):
                if n == 1 and chain:
                    series = [d.device(f"Q{k}", f"WIDE-CONTACT-1NO{sfx}").no for k in range(1, chain + 1)]
                    d.series(strip[n].inner, *series, card.di_1[f"1{ch}"], wire=wire)
                    continue
                contact = d.device(f"F{n}", f"WIDE-CONTACT-1NO{sfx}")
                d.series(strip[n].inner, contact.no["13" + long], wire=wire)
                d.series(contact.no["14" + long], getattr(card, f"di_{n}")[f"{n}{ch}"], wire=wire)
            for n in (1, 2):
                switch = d.device(f"S{n}", f"WIDE-SWITCH-2P{sfx}")
                d.series((strip[7].inner if n == 1 else strip[7].outer), switch.sw["A" + long], wire=wire)
                d.series(switch.sw["B" + long], getattr(card, f"di_{6 + n}")[f"{6 + n}{ch}"], wire=wire)
        return fr.build(d, unit_document(cab))


def _widths(result: fr.BuildResult) -> str:
    return "; ".join(
        f"rows {[r.width for r in page.rows]} of {page.area.w}, widest symbol {max((s.outline.w, s.key) for s in page.symbols if s.outline)}"
        for page in result.drawings.values()
    )


@pytest.mark.rule("G09-PAGE")
@pytest.mark.parametrize("shape", SHAPES)
@pytest.mark.parametrize("salt", SALTS)
def test_no_row_is_wider_than_its_page_at_any_salt(shape: str, salt: str) -> None:
    result = _built(shape, salt)
    found = sorted({f.code for f in result.findings} & REFUSED)
    assert not found, f"{found}; {_widths(result)}"
