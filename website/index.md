# Fransys

Fransys is a Python toolkit for electrical cabinet and harness design. You write the design as a short Python script against a part library, and Fransys checks it as it builds. From that one model it produces the schematic PDF, the parts, terminal, cable and PLC lists, and the KiCad and WAGO exports.

--8<-- "site-src/guide/index.md:install"

## An example

This script builds a small motor starter from the demo parts and writes one PDF into `out/`.

```python
--8<-- "snippets/example.py"
```

The first schematic page of that PDF:

[![The motor starter's first schematic page](assets/home.png)](assets/home.png)

## Where next

- [The guide](guide/index.md): every consumer task with its one spelling.
- [The part-file contract](contracts/part-file.md): how a part library is written.
- [The examples gallery](examples/index.md): whole designs, their PDFs and exports.
- [The API reference](api/index.md): every name the public surface exports.
- [The repository](https://github.com/OleJBondahl/fransys).

Fransys is released under the MIT licence.
