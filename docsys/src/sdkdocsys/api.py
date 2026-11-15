"""Static public-API snapshot and diff for ``splunklib``.

Uses ``ast`` only, so the SDK is never imported (no optional dependencies needed, and
no side effects). A snapshot maps qualified names to a signature and a docstring hash.
Diffing two snapshots tells the pipeline which docs are affected by an SDK change.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import tomllib
from pathlib import Path
from typing import Any

Snapshot = dict[str, Any]

# Container behavior lives in dunder methods, which the public API listing skips.
PROTOCOLS = {
    "__contains__": "`in`",
    "__iter__": "iteration",
    "__len__": "len()",
    "__getitem__": "indexing by name",
}


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    sig = f"({ast.unparse(node.args)})"
    if node.returns is not None:
        sig += f" -> {ast.unparse(node.returns)}"
    return sig


def _doc_hash(node: ast.AST) -> str:
    doc = ast.get_docstring(node) or ""  # type: ignore[arg-type]
    return hashlib.sha256(doc.encode()).hexdigest()[:12]


# Stored docstring length. The reviewer sees these for the symbols a page names, so cutting a
# long docstring short (the parameter list is usually last) hides facts it is asked to check.
DOC_LIMIT = 4000


def _entry(kind: str, node: ast.AST, sig: str = "") -> dict[str, Any]:
    return {
        "kind": kind,
        "sig": sig,
        "has_doc": bool(ast.get_docstring(node)),  # type: ignore[arg-type]
        "doc": (ast.get_docstring(node) or "")[:DOC_LIMIT],  # type: ignore[arg-type]
        "doc_hash": _doc_hash(node),
        "line": getattr(node, "lineno", 0),
    }


def _module_name(pkg_dir: Path, path: Path) -> str | None:
    parts = list(path.relative_to(pkg_dir.parent).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    if any(p.startswith("_") for p in parts):
        return None
    return ".".join(parts)


def snapshot(pkg_dir: Path) -> Snapshot:
    """Return ``{"meta": {...}, "symbols": {qualified_name: entry}}`` for a package dir."""
    symbols: dict[str, dict[str, Any]] = {}
    for path in sorted(pkg_dir.rglob("*.py")):
        module = _module_name(pkg_dir, path)
        if module is None:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        symbols[module] = _entry("module", tree)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if not node.name.startswith("_"):
                    symbols[f"{module}.{node.name}"] = _entry("function", node, _signature(node))
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                cls = f"{module}.{node.name}"
                symbols[cls] = _entry("class", node)
                symbols[cls]["protocols"] = [
                    PROTOCOLS[m.name]
                    for m in node.body
                    if isinstance(m, ast.FunctionDef) and m.name in PROTOCOLS
                ]
                for member in node.body:
                    is_func = isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef)
                    if not is_func or member.name.startswith("_"):
                        continue
                    decorators = {ast.unparse(d) for d in member.decorator_list}
                    if any(d.endswith((".setter", ".deleter")) for d in decorators):
                        continue  # the getter already represents this attribute
                    kind = "property" if "property" in decorators else "method"
                    symbols[f"{cls}.{member.name}"] = _entry(kind, member, _signature(member))
    return {"meta": _meta(pkg_dir), "symbols": symbols}


def _meta(pkg_dir: Path) -> dict[str, str]:
    root = pkg_dir.parent
    version = "unknown"
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        version = tomllib.loads(pyproject.read_text())["project"].get("version", "unknown")
    try:
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    return {"sdk_version": version, "git_commit": commit}


def load(path: Path) -> Snapshot | None:
    return json.loads(path.read_text()) if path.exists() else None


def save(snap: Snapshot, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap, indent=1, sort_keys=True) + "\n")


def diff(old: Snapshot | None, new: Snapshot) -> dict[str, list[str]]:
    """Compare snapshots. With no baseline, every symbol counts as added."""
    old_syms = (old or {}).get("symbols", {})
    new_syms = new["symbols"]
    return {
        "added": sorted(k for k in new_syms if k not in old_syms),
        "removed": sorted(k for k in old_syms if k not in new_syms),
        "signature_changed": sorted(
            k for k in new_syms if k in old_syms and new_syms[k]["sig"] != old_syms[k]["sig"]
        ),
        "docs_changed": sorted(
            k
            for k in new_syms
            if k in old_syms
            and new_syms[k]["sig"] == old_syms[k]["sig"]
            and new_syms[k]["doc_hash"] != old_syms[k]["doc_hash"]
        ),
    }


def changed_symbols(d: dict[str, list[str]]) -> set[str]:
    return {s for group in d.values() for s in group}


def covers(prefixes: list[str], symbol: str) -> bool:
    """True when ``symbol`` is one of ``prefixes`` or lives beneath one of them."""
    return any(symbol == p or symbol.startswith(p + ".") for p in prefixes)


def docstring_coverage(snap: Snapshot) -> float:
    syms = [e for e in snap["symbols"].values() if e["kind"] != "module"]
    return sum(e["has_doc"] for e in syms) / len(syms) if syms else 1.0
