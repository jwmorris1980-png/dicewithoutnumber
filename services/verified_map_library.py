"""Read and search the locally reviewed verified-map manifest."""

from __future__ import annotations

import json
import random
import re
from pathlib import Path


MANIFEST = Path(__file__).resolve().parents[1] / "data" / "verified_maps.json"
QUERY_STOPWORDS = {"a", "an", "the", "map", "maps", "please", "show", "find", "give", "me"}
RPG_PLAY_TERMS = {
    "battlemap",
    "battlemaps",
    "dungeon",
    "floorplan",
    "floorplans",
    "encounter",
    "tactical",
    "vtt",
    "deckplan",
    "deckplans",
}
NON_RPG_TERMS = {
    "prison",
    "museum",
    "county",
    "state",
    "habs",
    "haer",
    "facility",
    "engineering",
}


def load_verified_maps() -> list[dict]:
    try:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return payload.get("images", []) if isinstance(payload, dict) else []


def is_rpg_play_map(entry: dict) -> bool:
    words = set(re.findall(r"[a-z0-9]+", str(entry.get("name") or "").lower()))
    return bool(words.intersection(RPG_PLAY_TERMS)) and not bool(words.intersection(NON_RPG_TERMS))


def find_verified_map(query: str) -> dict | None:
    requested = {
        word
        for word in re.findall(r"[a-z0-9]+", str(query).lower())
        if word not in QUERY_STOPWORDS
    }
    if not requested:
        return random.choice(load_verified_maps()) if load_verified_maps() else None
    matches = []
    for entry in load_verified_maps():
        if not is_rpg_play_map(entry):
            continue
        searchable = " ".join(
            [str(entry.get("name") or ""), " ".join(entry.get("tags") or [])]
        ).lower()
        words = set(re.findall(r"[a-z0-9]+", searchable))
        score = len(requested.intersection(words))
        if requested.issubset(words):
            matches.append((score, entry))
    if not matches:
        return None
    best_score = max(score for score, _ in matches)
    return random.choice([entry for score, entry in matches if score == best_score])
