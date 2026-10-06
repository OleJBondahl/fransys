"""A minimal stdlib reader for KiCad's S-expression format, with no notion of what a file means."""

import re

_TOKEN = re.compile(
    r'\s*(?:(?P<open>\()|(?P<close>\))|"(?P<string>(?:[^"\\]|\\.)*)"|(?P<atom>[^\s()"]+))'
)
_ESCAPES = {"n": "\n", "r": "\r"}

type Sexpr = list[str | Sexpr]


def _unescape(text: str) -> str:
    return re.sub(r"\\(.)", lambda match: _ESCAPES.get(match[1], match[1]), text)


def _tokens(text: str) -> list[tuple[str, str]]:
    """`(kind, text)` for every token: `open`, `close`, `string` (still escaped) or `atom`."""
    found: list[tuple[str, str]] = []
    position = 0
    text = text.rstrip()
    while position < len(text):
        match = _TOKEN.match(text, position)
        if match is None or match.lastgroup is None:
            msg = f"cannot read a token at offset {position}"
            raise ValueError(msg)
        found.append((match.lastgroup, match[match.lastgroup]))
        position = match.end()
    return found


def _read(tokens: list[tuple[str, str]], start: int) -> tuple[Sexpr, int]:
    """The list whose opening parenthesis is `tokens[start]`, and the index after its closing."""
    if start >= len(tokens) or tokens[start][0] != "open":
        msg = "expected an opening parenthesis"
        raise ValueError(msg)
    node: Sexpr = []
    position = start + 1
    while position < len(tokens):
        kind, text = tokens[position]
        if kind == "close":
            return node, position + 1
        if kind == "open":
            child, position = _read(tokens, position)
            node.append(child)
        else:
            node.append(_unescape(text) if kind == "string" else text)
            position += 1
    msg = "an unclosed parenthesis"
    raise ValueError(msg)


def parse_sexpr(text: str) -> Sexpr:
    """Read one s-expression into nested lists of `str`; `ValueError` unless it is exactly one."""
    tokens = _tokens(text)
    if not tokens:
        msg = "no s-expression found in the text"
        raise ValueError(msg)
    node, end = _read(tokens, 0)
    if end != len(tokens):
        msg = "text after the top-level expression"
        raise ValueError(msg)
    return node
