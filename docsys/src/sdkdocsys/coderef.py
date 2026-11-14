"""``coderef``: pull tested example code into docs at build time.

Docs reference code, they do not contain it. In MyST markdown (colon fence, so the
page has no backtick code fences)::

    :::{coderef} examples/oneshot_search.py
    :region: search
    :::

Regions are delimited inside the example file by marker comments::

    # region: search
    ...
    # endregion: search

Omit ``:region:`` to include the whole file. The rendered block links back to the
source file, which is the single maintained and tested copy.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

from docutils import nodes
from docutils.parsers.rst import Directive, directives

_START = re.compile(r"^\s*#\s*region:\s*(?P<name>[\w.-]+)\s*$")
_END = re.compile(r"^\s*#\s*endregion:\s*(?P<name>[\w.-]+)\s*$")


class RegionError(ValueError):
    pass


def list_regions(text: str) -> list[str]:
    return [m["name"] for line in text.splitlines() if (m := _START.match(line))]


def extract(text: str, region: str | None) -> str:
    """Return the code for ``region`` (marker lines removed, dedented) or the whole file."""
    lines = text.splitlines()
    if region is None:
        return "\n".join(ln for ln in lines if not (_START.match(ln) or _END.match(ln))) + "\n"
    out: list[str] = []
    inside = False
    for line in lines:
        if (m := _START.match(line)) and m["name"] == region:
            inside = True
        elif (m := _END.match(line)) and m["name"] == region:
            return textwrap.dedent("\n".join(out)).strip("\n") + "\n"
        elif inside and not (_START.match(line) or _END.match(line)):
            out.append(line)
    raise RegionError(f"region {region!r} not found or not closed")


class CodeRef(Directive):
    required_arguments = 1
    option_spec = {
        "region": directives.unchanged,
        "caption": directives.unchanged,
        "no-link": directives.flag,
    }

    def run(self) -> list[nodes.Node]:
        env = self.state.document.settings.env
        root = Path(env.config.coderef_root)
        rel = self.arguments[0]
        path = (root / rel).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise self.error(f"coderef: {rel} not found under {root}")
        env.note_dependency(str(path))
        try:
            code = extract(path.read_text(encoding="utf-8"), self.options.get("region"))
        except RegionError as exc:
            raise self.error(f"coderef: {rel}: {exc}") from exc
        block = nodes.literal_block(code, code)
        block["language"] = "python"
        block["highlight_args"] = {}
        caption = self.options.get("caption") or rel
        if "no-link" not in self.options and env.config.coderef_source_url:
            url = f"{env.config.coderef_source_url.rstrip('/')}/{rel}"
            ref = nodes.reference(caption, caption, refuri=url)
            return [nodes.paragraph("", "", nodes.strong("", "Source: "), ref), block]
        return [
            nodes.paragraph("", "", nodes.strong("", "Source: "), nodes.literal("", caption)),
            block,
        ]


def setup(app):  # pragma: no cover - exercised by the Sphinx build
    app.add_config_value("coderef_root", ".", "env")
    app.add_config_value("coderef_source_url", "", "env")
    app.add_directive("coderef", CodeRef)
    return {"version": "0.1", "parallel_read_safe": True}
