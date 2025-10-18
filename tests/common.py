from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Dict, List, Literal, Optional

Domain = Literal["core_api", "agentic", "cv", "llm"]

# --------------------------------------------------------------------------------------
# Paths & small utils
# --------------------------------------------------------------------------------------

def project_root() -> Path:
    """
    Return the repository root (parent of the 'tests' folder).
    """
    return Path(__file__).resolve().parent.parent


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def json_files(*dirs: str | Path, pattern: str = "*.json") -> List[Path]:
    """
    Return a sorted list of JSON files matching `pattern` in the given directories.

    Examples:
        json_files("examples/core_api/valid")
        json_files(project_root() / "examples" / "llm" / "invalid")
    """
    if not dirs:
        raise ValueError("json_files() expects at least one directory path.")

    out: list[Path] = []
    for d in dirs:
        dpath = Path(d).resolve()
        if not dpath.exists():
            raise FileNotFoundError(f"Directory not found: {dpath}")
        if not dpath.is_dir():
            raise NotADirectoryError(f"Not a directory: {dpath}")
        out.extend(p for p in dpath.glob(pattern) if p.is_file())

    # Deterministic order across platforms
    out.sort(key=lambda p: p.name.casefold())
    return out


# --------------------------------------------------------------------------------------
# Schema discovery for each domain
# --------------------------------------------------------------------------------------

def _schema_basenames(domain: Domain) -> List[str]:
    """
    Possible schema filenames for a given domain, in priority order.
    """
    return [
        f"{domain}.schema.json",
        f"{domain}_schema.json",
        f"{domain}.json",
    ]


def _schema_search_dirs(domain: Domain) -> List[Path]:
    """
    Places we look for schemas, in priority order.
    """
    root = project_root()
    return [
        root / "schemas",
        root / "schema",
        root / "ulog" / "schemas",
        root / "tests" / "schemas",
        root / "examples" / domain,
    ]


def _find_schema_path(domain: Domain) -> Optional[Path]:
    """
    Return the first existing schema path for the domain, or None if not found.
    """
    for d in _schema_search_dirs(domain):
        for base in _schema_basenames(domain):
            candidate = d / base
            if candidate.exists():
                return candidate.resolve()
    return None


@lru_cache(maxsize=None)
def load_schema(domain: Domain, required: bool = False) -> dict:
    """
    Load and return the JSON Schema (dict) for `domain`.

    If `required` is True, raise FileNotFoundError when not found.
    Otherwise, return {} when not found (useful when tests import
    many schemas but only exercise one).
    """
    path = _find_schema_path(domain)
    if not path:
        if required:
            searched = []
            for d in _schema_search_dirs(domain):
                for base in _schema_basenames(domain):
                    searched.append(str((d / base).resolve()))
            raise FileNotFoundError(
                f"Schema for domain '{domain}' not found. Searched:\n" + "\n".join(searched)
            )
        return {}
    return _load_json(path)


# ---------- Schema constants ----------

# Relative wrapper filenames (what the tests/fixtures expect)
CORE_API_SCHEMA: str = "core_api.schema.json"
AGENTIC_SCHEMA: str = "agentic.schema.json"
CV_SCHEMA: str = "cv.schema.json"
LLM_SCHEMA: str = "llm.schema.json"

# If any test needs the loaded dict, use these:
CORE_API_SCHEMA_OBJ: dict = load_schema("core_api", required=False)
AGENTIC_SCHEMA_OBJ: dict = load_schema("agentic", required=False)
CV_SCHEMA_OBJ: dict = load_schema("cv", required=False)
LLM_SCHEMA_OBJ: dict = load_schema("llm", required=False)

SCHEMA_BY_DOMAIN: Dict[Domain, str] = {
    "core_api": CORE_API_SCHEMA,
    "agentic": AGENTIC_SCHEMA,
    "cv": CV_SCHEMA,
    "llm": LLM_SCHEMA,
}

# --------------------------------------------------------------------------------------
# Example file helpers (by domain)
# --------------------------------------------------------------------------------------

def examples_dir(domain: Domain) -> Path:
    """
    Base examples directory for a domain.
    """
    return project_root() / "examples" / domain


def valid_examples(domain: Domain, pattern: str = "*.json") -> List[Path]:
    """
    All 'valid' example JSON files for a domain.
    """
    return json_files(examples_dir(domain) / "valid", pattern=pattern)


def invalid_examples(domain: Domain, pattern: str = "*.json") -> List[Path]:
    """
    All 'invalid' example JSON files for a domain.
    """
    return json_files(examples_dir(domain) / "invalid", pattern=pattern)


__all__ = [
    "Domain",
    "project_root",
    "json_files",
    "load_schema",
    "CORE_API_SCHEMA",
    "AGENTIC_SCHEMA",
    "CV_SCHEMA",
    "LLM_SCHEMA",
    "SCHEMA_BY_DOMAIN",
    "examples_dir",
    "valid_examples",
    "invalid_examples",
]
