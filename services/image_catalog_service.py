"""
ImageCatalogService — bot-side async HTTP client for the image catalog server.

The catalog server is a separate free-tier deployment (Render.com / Railway).
This service queries it to retrieve curated free maps & portraits for SWN/CWN/WWN,
each carrying full attribution/source info.
"""

import logging
import os
from pathlib import Path
from typing import Optional

# On the server the admin key lives in a file (never in env for security)
def _load_admin_key() -> str:
    file_path = os.environ.get("IMAGE_ADMIN_KEY_FILE", "")
    if file_path and Path(file_path).exists():
        return Path(file_path).read_text().strip()
    return os.environ.get("IMAGE_ADMIN_KEY", "")

import aiohttp

log = logging.getLogger(__name__)

# The catalog runs on the same Oracle server on port 8001.
# Bot connects internally; set IMAGE_CATALOG_URL to override (e.g. for local dev).
_DEFAULT_URL = "http://127.0.0.1:8001"
CATALOG_URL = os.environ.get("IMAGE_CATALOG_URL", _DEFAULT_URL).rstrip("/")


class ImageCatalogService:
    """Async client for the DICEwithoutNumber image catalog server."""

    def __init__(self, base_url: str = CATALOG_URL, timeout: int = 12):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(
        self,
        image_type: Optional[str] = None,
        tags: Optional[str] = None,
        system: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Search the catalog.

        Parameters
        ----------
        image_type : "map" or "portrait" (optional)
        tags       : comma-separated tag string, e.g. "space,station"
        system     : "SWN", "CWN", or "WWN"
        query      : free-text search
        limit      : max results to return (1–100)
        """
        params: dict = {"limit": limit}
        if image_type:
            params["type"] = image_type
        if tags:
            params["tags"] = tags
        if system:
            params["system"] = system
        if query:
            params["q"] = query

        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/images", params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("results", [])
        except Exception as exc:
            log.warning("ImageCatalogService search failed: %s", exc)
            return []

    async def random_image(
        self,
        image_type: Optional[str] = None,
        tags: Optional[str] = None,
        system: Optional[str] = None,
    ) -> Optional[dict]:
        """Return one random image matching the filters, or None on failure."""
        params: dict = {}
        if image_type:
            params["type"] = image_type
        if tags:
            params["tags"] = tags
        if system:
            params["system"] = system

        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/random", params=params) as resp:
                if resp.status == 404:
                    return None
                resp.raise_for_status()
                return await resp.json()
        except Exception as exc:
            log.warning("ImageCatalogService random failed: %s", exc)
            return None

    async def get_by_id(self, image_id: str) -> Optional[dict]:
        """Fetch a specific image by ID."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/images/{image_id}") as resp:
                if resp.status == 404:
                    return None
                resp.raise_for_status()
                return await resp.json()
        except Exception as exc:
            log.warning("ImageCatalogService get_by_id failed: %s", exc)
            return None

    async def list_tags(self) -> list[str]:
        """Return all tags available in the catalog."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/tags") as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as exc:
            log.warning("ImageCatalogService list_tags failed: %s", exc)
            return []

    async def add_image(self, entry: dict, admin_key: str) -> dict:
        """
        Admin: add a new image entry to the catalog.

        entry must include: id, type, name, url, source_page,
                            artist, license, attribution
        """
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/admin/images",
                json=entry,
                headers={"x-api-key": admin_key},
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientResponseError as exc:
            text = await exc.response.text() if exc.response else ""
            log.error("ImageCatalogService add_image error %s: %s", exc.status, text)
            raise

    async def is_available(self) -> bool:
        """Check whether the catalog server is reachable."""
        try:
            session = await self._get_session()
            async with session.get(self.base_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return resp.status == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Helper: build a Discord-ready embed dict from a catalog entry
    # ------------------------------------------------------------------

    @staticmethod
    def displayable_image_url(entry: dict) -> Optional[str]:
        """Return a direct image URL Discord can render, never a collection page."""
        for key in ("url", "thumbnail_url"):
            value = str(entry.get(key) or "").strip()
            path = value.lower().split("?", 1)[0]
            if value.startswith(("http://", "https://")) and path.endswith(
                (".png", ".jpg", ".jpeg", ".webp", ".gif")
            ):
                return value
        return None

    @staticmethod
    def build_embed_data(entry: dict) -> dict:
        """
        Returns a dict of keyword arguments suitable for constructing a
        discord.Embed from a catalog entry.
        """
        kind = entry.get("type", "image").title()
        name = entry.get("name", "Unnamed")
        description = entry.get("description", "")
        attribution = entry.get("attribution", "")
        license_text = entry.get("license", "Unknown")
        license_url = entry.get("license_url", "")
        source_page = entry.get("source_page", "")
        artist = entry.get("artist", "Unknown")
        systems = ", ".join(entry.get("system", []))
        tags = ", ".join(entry.get("tags", []))
        image_url = ImageCatalogService.displayable_image_url(entry)

        license_link = f"[{license_text}]({license_url})" if license_url else license_text
        source_link = f"[Source page]({source_page})" if source_page else ""

        embed_dict = {
            "title": f"{name} — {kind}",
            "description": description,
            "fields": [
                {"name": "Artist", "value": artist, "inline": True},
                {"name": "License", "value": license_link, "inline": True},
                {"name": "Systems", "value": systems or "General", "inline": True},
                {"name": "Tags", "value": tags or "—", "inline": False},
                {"name": "Attribution", "value": attribution, "inline": False},
            ],
            "footer": "All images are free for personal use — always credit the original artist.",
            "url": source_page,
            "image_url": image_url,
            "source_link": source_link,
        }
        return embed_dict
