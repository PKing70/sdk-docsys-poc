"""Sphinx configuration for the combined guides + API reference site.

Reuses the SDK's autodoc approach but lives outside the SDK tree, so the SDK's own
``docs/conf.py`` is untouched. ``sdkdocsys build`` stages content and runs Sphinx with
this config directory.
"""

import os
import sys
import tomllib
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # docsys/
REPO = ROOT.parent  # the SDK checkout
sys.path[:0] = [str(REPO), str(ROOT / "src")]

_project = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]
project = "Splunk SDK for Python"
copyright = f"2011-{datetime.now().year} Splunk, Inc."
release = _project["version"]
version = ".".join(release.split(".")[:2])

extensions = ["sphinx.ext.autodoc", "sphinx.ext.ifconfig", "myst_parser", "sdkdocsys.coderef"]
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
master_doc = "index"
exclude_patterns = ["_build"]
myst_enable_extensions = ["colon_fence"]
myst_heading_anchors = 3

# splunklib.ai needs its optional dependencies importable (install the `reference` extra).
# Mocking pydantic breaks class definitions, so only provider SDKs that are never required
# at import time are mocked.
autodoc_mock_imports = ["langchain_anthropic", "langchain_openai", "langchain_google_genai"]

html_theme = "alabaster"
html_title = "Splunk SDK for Python"
pygments_style = "sphinx"

coderef_root = str(ROOT)
coderef_source_url = os.environ.get("DOCSYS_SOURCE_URL", "")
