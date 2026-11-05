"""A connector part file for the field cases that write their own library: `part_toml` and its `LIBRARY`."""

LIBRARY = 'schema = 2\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
_PART = """schema = 2

[part]
mpn = "{mpn}"
manufacturer = "Demo"
description = "{mpn}"
category = "connector"
class_code = "J"

[[function]]
name = "x"
kind = "connector"
symbol = "connector-fixed"
ports = [{ports}]

[function.connector]
style = "{style}"
pincount = {n}
gender = "{gender}"
"""


def part_toml(mpn: str, n: int, gender: str) -> str:
    ports = ", ".join(f'{{ name = "{i}", role = "generic", symbol_port = "{"in" if i % 2 else "out"}" }}' for i in range(1, n + 1))
    return _PART.format(mpn=mpn, ports=ports, style=f"{mpn.lower()}-{n}p", n=n, gender=gender)
