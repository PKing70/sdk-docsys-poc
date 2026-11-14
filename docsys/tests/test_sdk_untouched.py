"""R1: the doc system must never modify SDK sources."""

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SDK_PATHS = ["splunklib", "docs", "tests", "examples", "pyproject.toml", "Makefile", "uv.lock"]


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


def test_sdk_paths_match_upstream():
    base = next(
        (
            r
            for r in ("upstream/HEAD", "upstream/main", "upstream/master")
            if _git("rev-parse", "--verify", "--quiet", r).returncode == 0
        ),
        None,
    )
    if base is None:
        pytest.skip("no upstream ref to compare against")
    out = _git("diff", "--stat", base, "--", *SDK_PATHS)
    assert out.returncode == 0 and out.stdout.strip() == "", out.stdout
