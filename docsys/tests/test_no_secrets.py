"""Nothing credential-shaped may be committed. Runs in CI too, before anything is published."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCAN = [REPO / "docsys", REPO / ".github" / "workflows" / "docsys.yml"]
SKIP_DIRS = {".venv", "_build", "__pycache__", ".pytest_cache", ".ruff_cache"}
PATTERNS = {
    "Anthropic API key": re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    "AWS access key id": re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"),
    "JWT / SCS token": re.compile(
        r"\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}"
    ),
    "bearer token assignment": re.compile(
        r"AWS_BEARER_TOKEN_BEDROCK\s*=\s*['\"][A-Za-z0-9._-]{20,}['\"]"
    ),
    "private key block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}


def _files():
    for root in SCAN:
        paths = [root] if root.is_file() else root.rglob("*")
        for p in paths:
            if p.is_file() and not (SKIP_DIRS & set(p.parts)) and p.stat().st_size < 2_000_000:
                yield p


def test_no_credentials_in_project_files():
    hits = []
    for path in _files():
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                hits.append(f"{path.relative_to(REPO)}: {label}")
    assert not hits, "credential-shaped strings found:\n" + "\n".join(hits)


def test_secret_files_are_gitignored():
    ignore = (REPO / "docsys" / ".gitignore").read_text()
    for entry in (".env", "*.pem"):
        assert entry in ignore, f"{entry} must be gitignored"
