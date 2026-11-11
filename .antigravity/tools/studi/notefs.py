"""studi.notefs - scritture atomiche, frontmatter YAML piatto, citekey stabili."""
from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Optional

import yaml


def atomic_write(path: Path, text: str) -> None:
    """File temporaneo nella stessa cartella + fsync + os.replace: Obsidian non vede mai file a meta'."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def slug(s: str, n: int = 40) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:n] or "untitled"


def _surname(author: str) -> str:
    a = author.strip()
    if not a:
        return "anon"
    return a.split(",")[0] if "," in a else a.split()[-1]


def make_citekey(authors: list[str], year: Optional[int], title: str, doi: str) -> str:
    first = slug(_surname(authors[0]), 20) if authors else "anon"
    return f"{first}{year or 'nd'}-{hashlib.sha1(doi.encode()).hexdigest()[:6]}"


def dump_frontmatter(d: dict[str, Any]) -> str:
    clean = {k: v for k, v in d.items() if v is not None}
    body = yaml.safe_dump(clean, sort_keys=False, allow_unicode=True, default_flow_style=False, width=1000)
    return f"---\n{body}---\n"


def read_frontmatter(path: Path) -> dict[str, Any]:
    t = path.read_text(encoding="utf-8")
    if not t.startswith("---\n"):
        return {}
    end = t.find("\n---", 4)
    return (yaml.safe_load(t[4:end]) or {}) if end > 0 else {}


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
