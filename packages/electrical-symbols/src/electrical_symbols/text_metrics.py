"""Per-glyph advance table for the drawing font, as data (docs/design/geometry.md 5.3).

Generated offline from Liberation Serif Regular (SIL OFL 1.1, metric-compatible with Times
New Roman) and committed; the package never opens a font.

Source: Version 2.1.5 of the font, release liberation-fonts-ttf-2.1.5,
file LiberationSerif-Regular.ttf, sha256
058ea80864aef09a23f45cbec2bb5400bc3dfbdea01c3f10538a21fcb497fb74.
Read with fontTools 4.65.0 (`uvx --from fonttools==4.65.0 ttx`) by a script
in `claude-tools/` that is not committed.

The font has 2048 units per em. Each advance is converted to thousandths of an em and
rounded up, so a width estimated from this table is never below the font's own. It covers
Basic Latin, Latin-1 Supplement, the dashes, the euro sign and the ohm signs; any other glyph
is estimated with the widest advance (`text.py`).
"""

FONT_NAME = "Liberation Serif"
UNITS_PER_EM = 1000

# glyph -> advance in thousandths of an em
ADVANCES: frozendict[str, int] = frozendict(
    {
        " ": 250,
        "!": 334,
        '"': 409,
        "#": 500,
        "$": 500,
        "%": 834,
        "&": 778,
        "'": 181,
        "(": 334,
        ")": 334,
        "*": 500,
        "+": 564,
        ",": 250,
        "-": 334,
        ".": 250,
        "/": 278,
        "0": 500,
        "1": 500,
        "2": 500,
        "3": 500,
        "4": 500,
        "5": 500,
        "6": 500,
        "7": 500,
        "8": 500,
        "9": 500,
        ":": 278,
        ";": 278,
        "<": 564,
        "=": 564,
        ">": 564,
        "?": 444,
        "@": 921,
        "A": 723,
        "B": 667,
        "C": 667,
        "D": 723,
        "E": 611,
        "F": 557,
        "G": 723,
        "H": 723,
        "I": 334,
        "J": 390,
        "K": 723,
        "L": 611,
        "M": 890,
        "N": 723,
        "O": 723,
        "P": 557,
        "Q": 723,
        "R": 667,
        "S": 557,
        "T": 611,
        "U": 723,
        "V": 723,
        "W": 944,
        "X": 723,
        "Y": 723,
        "Z": 611,
        "[": 334,
        "\\": 278,
        "]": 334,
        "^": 470,
        "_": 500,
        "`": 334,
        "a": 444,
        "b": 500,
        "c": 444,
        "d": 500,
        "e": 444,
        "f": 334,
        "g": 500,
        "h": 500,
        "i": 278,
        "j": 278,
        "k": 500,
        "l": 278,
        "m": 778,
        "n": 500,
        "o": 500,
        "p": 500,
        "q": 500,
        "r": 334,
        "s": 390,
        "t": 278,
        "u": 500,
        "v": 500,
        "w": 723,
        "x": 500,
        "y": 500,
        "z": 444,
        "{": 480,
        "|": 201,
        "}": 480,
        "~": 542,
        "\u00a0": 250,  # NO-BREAK SPACE
        "\u00a1": 334,  # INVERTED EXCLAMATION MARK
        "\u00a2": 500,  # CENT SIGN
        "\u00a3": 500,  # POUND SIGN
        "\u00a4": 500,  # CURRENCY SIGN
        "\u00a5": 500,  # YEN SIGN
        "\u00a6": 201,  # BROKEN BAR
        "\u00a7": 500,  # SECTION SIGN
        "\u00a8": 334,  # DIAERESIS
        "\u00a9": 760,  # COPYRIGHT SIGN
        "\u00aa": 276,  # FEMININE ORDINAL INDICATOR
        "\u00ab": 500,  # LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
        "\u00ac": 564,  # NOT SIGN
        "\u00ad": 334,  # SOFT HYPHEN
        "\u00ae": 760,  # REGISTERED SIGN
        "\u00af": 500,  # MACRON
        "\u00b0": 400,  # DEGREE SIGN
        "\u00b1": 549,  # PLUS-MINUS SIGN
        "\u00b2": 300,  # SUPERSCRIPT TWO
        "\u00b3": 300,  # SUPERSCRIPT THREE
        "\u00b4": 334,  # ACUTE ACCENT
        "\u00b5": 577,  # MICRO SIGN
        "\u00b6": 454,  # PILCROW SIGN
        "\u00b7": 334,  # MIDDLE DOT
        "\u00b8": 334,  # CEDILLA
        "\u00b9": 300,  # SUPERSCRIPT ONE
        "\u00ba": 311,  # MASCULINE ORDINAL INDICATOR
        "\u00bb": 500,  # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
        "\u00bc": 750,  # VULGAR FRACTION ONE QUARTER
        "\u00bd": 750,  # VULGAR FRACTION ONE HALF
        "\u00be": 750,  # VULGAR FRACTION THREE QUARTERS
        "\u00bf": 444,  # INVERTED QUESTION MARK
        "\u00c0": 723,  # LATIN CAPITAL LETTER A WITH GRAVE
        "\u00c1": 723,  # LATIN CAPITAL LETTER A WITH ACUTE
        "\u00c2": 723,  # LATIN CAPITAL LETTER A WITH CIRCUMFLEX
        "\u00c3": 723,  # LATIN CAPITAL LETTER A WITH TILDE
        "\u00c4": 723,  # LATIN CAPITAL LETTER A WITH DIAERESIS
        "\u00c5": 723,  # LATIN CAPITAL LETTER A WITH RING ABOVE
        "\u00c6": 890,  # LATIN CAPITAL LETTER AE
        "\u00c7": 667,  # LATIN CAPITAL LETTER C WITH CEDILLA
        "\u00c8": 611,  # LATIN CAPITAL LETTER E WITH GRAVE
        "\u00c9": 611,  # LATIN CAPITAL LETTER E WITH ACUTE
        "\u00ca": 611,  # LATIN CAPITAL LETTER E WITH CIRCUMFLEX
        "\u00cb": 611,  # LATIN CAPITAL LETTER E WITH DIAERESIS
        "\u00cc": 334,  # LATIN CAPITAL LETTER I WITH GRAVE
        "\u00cd": 334,  # LATIN CAPITAL LETTER I WITH ACUTE
        "\u00ce": 334,  # LATIN CAPITAL LETTER I WITH CIRCUMFLEX
        "\u00cf": 334,  # LATIN CAPITAL LETTER I WITH DIAERESIS
        "\u00d0": 723,  # LATIN CAPITAL LETTER ETH
        "\u00d1": 723,  # LATIN CAPITAL LETTER N WITH TILDE
        "\u00d2": 723,  # LATIN CAPITAL LETTER O WITH GRAVE
        "\u00d3": 723,  # LATIN CAPITAL LETTER O WITH ACUTE
        "\u00d4": 723,  # LATIN CAPITAL LETTER O WITH CIRCUMFLEX
        "\u00d5": 723,  # LATIN CAPITAL LETTER O WITH TILDE
        "\u00d6": 723,  # LATIN CAPITAL LETTER O WITH DIAERESIS
        "\u00d7": 564,  # MULTIPLICATION SIGN
        "\u00d8": 723,  # LATIN CAPITAL LETTER O WITH STROKE
        "\u00d9": 723,  # LATIN CAPITAL LETTER U WITH GRAVE
        "\u00da": 723,  # LATIN CAPITAL LETTER U WITH ACUTE
        "\u00db": 723,  # LATIN CAPITAL LETTER U WITH CIRCUMFLEX
        "\u00dc": 723,  # LATIN CAPITAL LETTER U WITH DIAERESIS
        "\u00dd": 723,  # LATIN CAPITAL LETTER Y WITH ACUTE
        "\u00de": 557,  # LATIN CAPITAL LETTER THORN
        "\u00df": 500,  # LATIN SMALL LETTER SHARP S
        "\u00e0": 444,  # LATIN SMALL LETTER A WITH GRAVE
        "\u00e1": 444,  # LATIN SMALL LETTER A WITH ACUTE
        "\u00e2": 444,  # LATIN SMALL LETTER A WITH CIRCUMFLEX
        "\u00e3": 444,  # LATIN SMALL LETTER A WITH TILDE
        "\u00e4": 444,  # LATIN SMALL LETTER A WITH DIAERESIS
        "\u00e5": 444,  # LATIN SMALL LETTER A WITH RING ABOVE
        "\u00e6": 667,  # LATIN SMALL LETTER AE
        "\u00e7": 444,  # LATIN SMALL LETTER C WITH CEDILLA
        "\u00e8": 444,  # LATIN SMALL LETTER E WITH GRAVE
        "\u00e9": 444,  # LATIN SMALL LETTER E WITH ACUTE
        "\u00ea": 444,  # LATIN SMALL LETTER E WITH CIRCUMFLEX
        "\u00eb": 444,  # LATIN SMALL LETTER E WITH DIAERESIS
        "\u00ec": 278,  # LATIN SMALL LETTER I WITH GRAVE
        "\u00ed": 278,  # LATIN SMALL LETTER I WITH ACUTE
        "\u00ee": 278,  # LATIN SMALL LETTER I WITH CIRCUMFLEX
        "\u00ef": 278,  # LATIN SMALL LETTER I WITH DIAERESIS
        "\u00f0": 500,  # LATIN SMALL LETTER ETH
        "\u00f1": 500,  # LATIN SMALL LETTER N WITH TILDE
        "\u00f2": 500,  # LATIN SMALL LETTER O WITH GRAVE
        "\u00f3": 500,  # LATIN SMALL LETTER O WITH ACUTE
        "\u00f4": 500,  # LATIN SMALL LETTER O WITH CIRCUMFLEX
        "\u00f5": 500,  # LATIN SMALL LETTER O WITH TILDE
        "\u00f6": 500,  # LATIN SMALL LETTER O WITH DIAERESIS
        "\u00f7": 549,  # DIVISION SIGN
        "\u00f8": 500,  # LATIN SMALL LETTER O WITH STROKE
        "\u00f9": 500,  # LATIN SMALL LETTER U WITH GRAVE
        "\u00fa": 500,  # LATIN SMALL LETTER U WITH ACUTE
        "\u00fb": 500,  # LATIN SMALL LETTER U WITH CIRCUMFLEX
        "\u00fc": 500,  # LATIN SMALL LETTER U WITH DIAERESIS
        "\u00fd": 500,  # LATIN SMALL LETTER Y WITH ACUTE
        "\u00fe": 500,  # LATIN SMALL LETTER THORN
        "\u00ff": 500,  # LATIN SMALL LETTER Y WITH DIAERESIS
        "\u03a9": 744,  # GREEK CAPITAL LETTER OMEGA
        "\u2013": 500,  # EN DASH
        "\u2014": 1000,  # EM DASH
        "\u20ac": 500,  # EURO SIGN
        "\u2126": 769,  # OHM SIGN
    }
)
