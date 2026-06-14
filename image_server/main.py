"""
DICEwithoutNumber Image Catalog Server
Free-tier deployable (Render.com / Railway / Fly.io)

Serves curated free maps & portraits for Stars Without Number /
Cities Without Number / Worlds Without Number by Kevin Crawford.
Every image has attribution and a source link.
"""

import json
import os
import random
import re
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# On Render the persistent disk is mounted at /var/data; fall back to local for dev
_DISK_PATH = Path("/var/data/catalog.json")
_LOCAL_PATH = Path(__file__).parent / "catalog.json"
CATALOG_PATH = _DISK_PATH if _DISK_PATH.parent.exists() else _LOCAL_PATH
ADMIN_API_KEY = os.environ.get("IMAGE_ADMIN_KEY", "")  # Set in Render env vars

app = FastAPI(
    title="DICEwithoutNumber Image Catalog",
    description="Free maps & portraits for SWN/CWN/WWN RPGs with full attribution.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Catalog helpers
# ---------------------------------------------------------------------------

def load_catalog() -> List[dict]:
    # On first Render deploy the persistent disk is empty — seed from the bundled file
    if not CATALOG_PATH.exists() and CATALOG_PATH != _LOCAL_PATH and _LOCAL_PATH.exists():
        import shutil
        shutil.copy(_LOCAL_PATH, CATALOG_PATH)
    if not CATALOG_PATH.exists():
        return []
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("images", [])


def save_catalog(images: List[dict]) -> None:
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump({"images": images}, f, indent=2, ensure_ascii=False)


def _tag_score(entry: dict, tags: List[str]) -> int:
    """Return how many query tags match entry tags (case-insensitive)."""
    entry_tags = set(t.lower() for t in entry.get("tags", []))
    return sum(1 for t in tags if t.lower() in entry_tags)


def search_catalog(
    images: List[dict],
    image_type: Optional[str],
    tags: List[str],
    system: Optional[str],
    query: Optional[str],
) -> List[dict]:
    results = images

    if image_type:
        results = [i for i in results if i.get("type", "").lower() == image_type.lower()]

    if system:
        results = [
            i for i in results
            if system.upper() in [s.upper() for s in i.get("system", [])]
        ]

    if query:
        q = query.lower()
        results = [
            i for i in results
            if q in i.get("name", "").lower()
            or q in i.get("description", "").lower()
            or any(q in t.lower() for t in i.get("tags", []))
        ]

    if tags:
        scored = [(i, _tag_score(i, tags)) for i in results]
        scored = [(i, s) for i, s in scored if s > 0] or [(i, 0) for i in results]
        scored.sort(key=lambda x: -x[1])
        results = [i for i, _ in scored]

    return results


# ---------------------------------------------------------------------------
# Auth (admin-only write operations)
# ---------------------------------------------------------------------------

def verify_admin(x_api_key: str = Header(default="")):
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Admin API key not configured on server.")
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key.")
    return True


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    images = load_catalog()
    types = {}
    for img in images:
        t = img.get("type", "unknown")
        types[t] = types.get(t, 0) + 1
    return {
        "service": "DICEwithoutNumber Image Catalog",
        "description": "Free curated maps & portraits for SWN/CWN/WWN RPGs",
        "total_images": len(images),
        "by_type": types,
        "endpoints": ["/api/images", "/api/random", "/api/tags", "/api/systems"],
    }


@app.get("/api/images")
def list_images(
    type: Optional[str] = Query(None, description="Filter by type: map or portrait"),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
    system: Optional[str] = Query(None, description="Game system: SWN, CWN, WWN"),
    q: Optional[str] = Query(None, description="Text search in name/description/tags"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Search the image catalog. Returns entries with full attribution."""
    images = load_catalog()
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    results = search_catalog(images, type, tag_list, system, q)
    total = len(results)
    page = results[offset : offset + limit]
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "results": page,
    }


@app.get("/api/images/{image_id}")
def get_image(image_id: str):
    """Get a single image by ID."""
    images = load_catalog()
    for img in images:
        if img.get("id") == image_id:
            return img
    raise HTTPException(status_code=404, detail=f"Image '{image_id}' not found.")


@app.get("/api/random")
def random_image(
    type: Optional[str] = Query(None, description="map or portrait"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    system: Optional[str] = Query(None, description="SWN, CWN, WWN"),
):
    """Return a random image, optionally filtered."""
    images = load_catalog()
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    pool = search_catalog(images, type, tag_list, system, None)
    if not pool:
        raise HTTPException(status_code=404, detail="No images match the given filters.")
    return random.choice(pool)


@app.get("/api/tags")
def list_tags():
    """Return all unique tags in the catalog."""
    images = load_catalog()
    tags: set = set()
    for img in images:
        tags.update(img.get("tags", []))
    return sorted(tags)


@app.get("/api/systems")
def list_systems():
    """Return all game systems referenced in the catalog."""
    images = load_catalog()
    systems: set = set()
    for img in images:
        systems.update(img.get("system", []))
    return sorted(systems)


# ---------------------------------------------------------------------------
# Admin: Add / Remove (protected by API key)
# ---------------------------------------------------------------------------

@app.post("/api/admin/images", dependencies=[Depends(verify_admin)])
def add_image(entry: dict):
    """
    Add a new image entry to the catalog.
    Required fields: id, type, name, url, source_page, artist, license, attribution
    """
    required = {"id", "type", "name", "url", "source_page", "artist", "license", "attribution"}
    missing = required - set(entry.keys())
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing fields: {missing}")

    images = load_catalog()
    ids = {i["id"] for i in images}
    if entry["id"] in ids:
        raise HTTPException(status_code=409, detail=f"ID '{entry['id']}' already exists.")

    entry.setdefault("tags", [])
    entry.setdefault("system", ["SWN", "CWN"])
    entry.setdefault("added", "")

    images.append(entry)
    save_catalog(images)
    return {"status": "added", "id": entry["id"]}


@app.delete("/api/admin/images/{image_id}", dependencies=[Depends(verify_admin)])
def delete_image(image_id: str):
    """Remove an image entry from the catalog."""
    images = load_catalog()
    new_images = [i for i in images if i.get("id") != image_id]
    if len(new_images) == len(images):
        raise HTTPException(status_code=404, detail=f"Image '{image_id}' not found.")
    save_catalog(new_images)
    return {"status": "deleted", "id": image_id}
