"""Write `derive/_text_widths.py` from the DejaVu Sans Condensed TTFs; no network.

Usage: `uv run python packages/fransys-model/scripts/write_text_widths.py`. Build-time tool: it
reads the two fonts under `electrical_symbols` with fontTools (a dev dependency) and writes
the tracked module of advance widths, in font units, for ASCII, Latin-1 and the few symbols
drawings print.
The font heights live in `electrical_symbols/library.toml`.
"""

import hashlib
import textwrap
from pathlib import Path
from typing import Any, cast

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "electrical-symbols" / "src" / "electrical_symbols" / "fonts"
TARGET = ROOT / "fransys-model" / "src" / "fransys_model" / "derive" / "_text_widths.py"
# ASCII, Latin-1 (without the C1 controls), and the dashes, ellipsis, euro and ohm signs
CODEPOINTS = (
    *range(0x20, 0x7F),
    *range(0xA0, 0x100),
    0x2013,
    0x2014,
    0x2026,
    0x20AC,
    0x2126,
    0x03A9,
)
_HEADER = '''"""DejaVu Sans Condensed advance widths, in font units; GENERATED, do not edit.

Written by `scripts/write_text_widths.py` from the two TTFs under
`electrical_symbols/fonts/` (Bitstream Vera licence), so one table serves every text
width (model-0190).
Each string holds `codepoint-in-hex=advance` pairs.
sha256 Regular {regular}
sha256 Bold    {bold}
"""

UNITS_PER_EM = {upem}

'''


def _pairs(font: TTFont) -> str:
    cmap: Any = font.getBestCmap()
    hmtx: Any = font["hmtx"]
    return " ".join(f"{cp:x}={hmtx[cmap[cp]][0]}" for cp in CODEPOINTS)


def _literal(name: str, pairs: str) -> str:
    lines = textwrap.wrap(pairs, width=90)
    body = "\n".join(f'    "{line} "' for line in lines).rstrip(' "')
    return f'{name} = (\n{body}"\n)\n\n'


def main() -> None:
    paths = {
        "Regular": FONTS / "DejaVuSansCondensed.ttf",
        "Bold": FONTS / "DejaVuSansCondensed-Bold.ttf",
    }
    fonts = {w: TTFont(p) for w, p in paths.items()}
    upems = {cast("Any", f["head"]).unitsPerEm for f in fonts.values()}
    assert len(upems) == 1, upems  # noqa: S101 - build-time script: stop on mixed units-per-em
    sha = {w: hashlib.sha256(p.read_bytes()).hexdigest() for w, p in paths.items()}
    text = _HEADER.format(
        regular=sha["Regular"],
        bold=sha["Bold"],
        upem=upems.pop(),
    )
    text += _literal("REGULAR_PAIRS", _pairs(fonts["Regular"]))
    text += _literal("BOLD_PAIRS", _pairs(fonts["Bold"]))
    TARGET.write_text(text.rstrip("\n") + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
