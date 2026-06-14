"""Build a reviewable RPG map library from Wikimedia Commons metadata."""

from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "verified_maps.json"
PROGRESS = ROOT / "data" / "verified_maps.progress.json"
API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "DICEwithoutNumber/1.0 (open-source RPG accessibility bot)"
ACCEPTED_LICENSE_MARKERS = (
    "cc0",
    "public domain",
    "cc by ",
    "cc-by-",
    "cc by-sa",
    "cc-by-sa",
)
SUBJECTS = {
    "dungeon": ["dungeon map", "dungeon floor plan"],
    "fantasy": ["fantasy map"],
    "city": ["city map", "town map"],
    "village": ["village map"],
    "castle": ["castle map", "fortress map"],
    "cave": ["cave map", "cavern map"],
    "island": ["fantasy island map", "island map"],
    "world": ["fantasy world map", "fictional world map"],
    "ship": ["ship deck plan", "spaceship floor plan"],
    "station": ["space station floor plan"],
    "temple": ["temple floor plan"],
    "tavern": ["tavern floor plan", "inn floor plan"],
    "battle": ["battle map", "battlemap"],
}


def clean_html(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value or "")).split())


def metadata_value(metadata: dict, key: str) -> str:
    return clean_html(str((metadata.get(key) or {}).get("value") or ""))


def accepted_license(metadata: dict) -> bool:
    text = " ".join(
        metadata_value(metadata, key)
        for key in ("LicenseShortName", "License", "UsageTerms", "LicenseUrl")
    ).lower()
    return any(marker in text for marker in ACCEPTED_LICENSE_MARKERS)


def direct_image(url: str) -> bool:
    path = str(url or "").lower().split("?", 1)[0]
    return path.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))


def subject_matches(title: str, subject: str) -> bool:
    words = set(re.findall(r"[a-z0-9]+", title.lower().replace("_", " ")))
    map_words = {"map", "maps", "battlemap", "battlemaps", "floorplan", "floorplans", "plan", "plans"}
    return subject in words and bool(words.intersection(map_words))


def request_json(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 4:
                raise
            wait = 15 * (attempt + 1)
            print(f"[verified-maps] Rate limited; waiting {wait}s...")
            time.sleep(wait)
    return {}


def search_query(subject: str, phrase: str, pages: int = 2) -> list[dict]:
    results: list[dict] = []
    continuation: dict = {}
    for _ in range(pages):
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrnamespace": "6",
            "gsrlimit": "50",
            "gsrsearch": phrase,
            "prop": "imageinfo",
            "iiprop": "url|mime|mediatype|extmetadata",
            "iiurlwidth": "1200",
            **continuation,
        }
        data = request_json(params)
        for page in (data.get("query") or {}).get("pages", {}).values():
            info = ((page.get("imageinfo") or [{}])[0])
            metadata = info.get("extmetadata") or {}
            title = str(page.get("title") or "").removeprefix("File:")
            image_url = info.get("thumburl") or info.get("url") or ""
            if (
                info.get("mediatype") != "BITMAP"
                or not direct_image(image_url)
                or not accepted_license(metadata)
                or not subject_matches(title, subject)
            ):
                continue
            results.append(
                {
                    "id": f"commons-{page.get('pageid')}",
                    "type": "map",
                    "name": title.rsplit(".", 1)[0].replace("_", " "),
                    "description": metadata_value(metadata, "ImageDescription"),
                    "tags": [subject, "verified", "wikimedia-commons"],
                    "url": image_url,
                    "thumbnail_url": info.get("thumburl") or "",
                    "source_page": info.get("descriptionurl") or "",
                    "artist": metadata_value(metadata, "Artist") or "Unknown creator",
                    "license": metadata_value(metadata, "LicenseShortName")
                    or metadata_value(metadata, "UsageTerms"),
                    "license_url": metadata_value(metadata, "LicenseUrl"),
                    "system": ["General RPG"],
                    "added": str(date.today()),
                    "attribution": metadata_value(metadata, "Credit")
                    or f"{title} via Wikimedia Commons.",
                    "verified_source": "Wikimedia Commons API imageinfo extmetadata",
                }
            )
        continuation = data.get("continue") or {}
        if not continuation:
            break
        time.sleep(0.4)
    return results


def build_library() -> list[dict]:
    try:
        progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        progress = {"completed": [], "images": []}
    completed = set(progress.get("completed", []))
    unique: dict[str, dict] = {entry["id"]: entry for entry in progress.get("images", [])}
    for subject, phrases in SUBJECTS.items():
        for phrase in phrases:
            key = f"{subject}:{phrase}"
            if key in completed:
                continue
            print(f"[verified-maps] Searching {phrase!r}...")
            for entry in search_query(subject, phrase):
                unique[entry["id"]] = entry
            completed.add(key)
            PROGRESS.write_text(
                json.dumps({"completed": sorted(completed), "images": list(unique.values())}, indent=2)
                + "\n",
                encoding="utf-8",
            )
            time.sleep(2)
    return sorted(unique.values(), key=lambda entry: (entry["tags"][0], entry["name"].lower()))


def main() -> int:
    images = build_library()
    payload = {
        "generated": str(date.today()),
        "policy": "Direct bitmap, subject-matched title, and reusable license metadata required.",
        "count": len(images),
        "images": images,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    PROGRESS.unlink(missing_ok=True)
    print(f"[verified-maps] Wrote {len(images)} verified maps to {OUTPUT}")
    return 0 if images else 1


if __name__ == "__main__":
    raise SystemExit(main())
