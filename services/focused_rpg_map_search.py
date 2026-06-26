"""Focused, no-cost RPG map search over trusted local sources."""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
APPROVED_MAPS = ROOT / "data" / "approved_rpg_maps.json"
LOCAL_CATALOG = ROOT / "image_server" / "catalog.json"

TRUSTED_SOURCE_DOMAINS = {
    "2minutetabletop.com",
    "commons.wikimedia.org",
    "dysonlogos.blog",
    "upload.wikimedia.org",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "find",
    "give",
    "map",
    "maps",
    "me",
    "of",
    "please",
    "search",
    "show",
    "the",
}

QUERY_EXPANSIONS = {
    "bar": {"bar", "tavern", "cantina", "inn"},
    "castle": {"castle", "fortress", "keep", "stronghold"},
    "cave": {"cave", "cavern", "underground", "grotto"},
    "city": {"city", "street", "streets", "urban", "town", "market"},
    "cyberpunk": {"cyberpunk", "sci-fi", "scifi", "neon", "corporate", "metro"},
    "desert": {"desert", "wasteland", "arid", "dunes"},
    "dungeon": {"dungeon", "crypt", "ruin", "ruins", "temple", "tomb"},
    "forest": {"forest", "woods", "wilderness", "path", "camp", "encampment"},
    "space": {"space", "station", "ship", "starship", "deckplan", "sector"},
    "town": {"town", "village", "settlement", "city", "street", "market", "center", "centre"},
    "village": {"village", "town", "settlement", "hamlet", "city", "market"},
}

QUALITY_TERMS = {
    "battlemap": 8,
    "battle": 5,
    "dungeon": 6,
    "encounter": 4,
    "floorplan": 5,
    "grid": 3,
    "map": 2,
    "tactical": 4,
    "vtt": 6,
}

GENERIC_RPG_TERMS = {"battle", "battlemap", "encounter", "vtt"}

BAD_TERMS = {
    "county",
    "earthquake",
    "geologic",
    "historical",
    "municipal",
    "railway",
    "real estate",
    "reference",
    "tour",
    "tourist",
    "transit",
}


def requested_map_terms(query: str) -> list[str]:
    return [
        word
        for word in re.findall(r"[a-z0-9-]+", str(query or "").lower())
        if word not in STOPWORDS
    ]


def expand_map_query(query: str) -> list[str]:
    words = requested_map_terms(query)
    expanded: set[str] = set(words)
    for word in words:
        expanded.update(QUERY_EXPANSIONS.get(word, set()))
    expanded.update({"battlemap", "battle", "vtt", "encounter"})
    return sorted(expanded)


def focused_map_search(query: str, limit: int = 1) -> list[dict]:
    terms = expand_map_query(query)
    explicit_terms = set(requested_map_terms(query))
    matches = []
    for entry in _load_entries():
        score = score_map_entry(entry, terms, explicit_terms=explicit_terms)
        if score > 0:
            matches.append((score, entry))
    matches.sort(key=lambda item: (-item[0], str(item[1].get("name") or "")))
    best = [entry for _, entry in matches[:limit]]
    if not best and not str(query or "").strip():
        best = _displayable_entries()
        random.shuffle(best)
        best = best[:limit]
    return best


def score_map_entry(entry: dict, terms: list[str], explicit_terms: set[str] | None = None) -> int:
    if str(entry.get("type") or "").lower() != "map":
        return 0
    if not _is_trusted_source(entry):
        return 0
    if not _displayable_url(entry):
        return 0

    searchable = _searchable_text(entry)
    if any(bad in searchable for bad in BAD_TERMS):
        return 0

    words = set(re.findall(r"[a-z0-9-]+", searchable))
    requested = set(terms)
    explicit_terms = explicit_terms or set()
    explicit_specific = explicit_terms - GENERIC_RPG_TERMS
    if explicit_specific and not all(term in words or term in searchable for term in explicit_specific):
        return 0
    specific_terms = requested - GENERIC_RPG_TERMS
    if specific_terms and not any(term in words or term in searchable for term in specific_terms):
        return 0
    score = 0
    for term in explicit_terms:
        if term in words or term in searchable:
            score += 25
    for term in requested:
        if term in words or term in searchable:
            score += 12 if term not in GENERIC_RPG_TERMS else 4
    for term, weight in QUALITY_TERMS.items():
        if term in words or term in searchable:
            score += weight
    if "hand-reviewed" in words or "verified" in words:
        score += 15
    if entry.get("verified_source"):
        score += 4
    return score


def _load_entries() -> list[dict]:
    entries: list[dict] = []
    for path in (APPROVED_MAPS, LOCAL_CATALOG):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        images = payload.get("images", []) if isinstance(payload, dict) else []
        if isinstance(images, list):
            entries.extend(item for item in images if isinstance(item, dict))
    return entries


def _displayable_entries() -> list[dict]:
    return [entry for entry in _load_entries() if _displayable_url(entry) and _is_trusted_source(entry)]


def _displayable_url(entry: dict) -> str:
    for key in ("url", "thumbnail_url"):
        value = str(entry.get(key) or "").strip()
        path = value.lower().split("?", 1)[0]
        if value.startswith(("http://", "https://")) and path.endswith(
            (".png", ".jpg", ".jpeg", ".webp", ".gif")
        ):
            return value
    return ""


def _is_trusted_source(entry: dict) -> bool:
    for key in ("source_page", "url", "thumbnail_url"):
        host = urlparse(str(entry.get(key) or "")).hostname or ""
        host = host.lower().removeprefix("www.")
        if host in TRUSTED_SOURCE_DOMAINS:
            return True
    return False


def _searchable_text(entry: dict) -> str:
    parts = [
        str(entry.get("id") or ""),
        str(entry.get("name") or ""),
        str(entry.get("description") or ""),
        " ".join(str(tag) for tag in entry.get("tags") or []),
        str(entry.get("source_page") or ""),
        str(entry.get("verified_source") or ""),
    ]
    return " ".join(parts).lower()
