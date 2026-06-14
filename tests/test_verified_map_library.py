import json

from services import verified_map_library


def test_verified_map_manifest_search(monkeypatch, tmp_path):
    manifest = tmp_path / "verified_maps.json"
    manifest.write_text(
        json.dumps(
            {
                "images": [
                    {"name": "Dungeon Map", "tags": ["dungeon"], "url": "https://example/map.png"},
                    {"name": "Fantasy City Map", "tags": ["city"], "url": "https://example/city.png"},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(verified_map_library, "MANIFEST", manifest)

    assert verified_map_library.find_verified_map("dungeon")["name"] == "Dungeon Map"
    assert verified_map_library.find_verified_map("show me a dungeon map")["name"] == "Dungeon Map"
    assert verified_map_library.find_verified_map("city") is None
    assert verified_map_library.find_verified_map("space station") is None


def test_verified_manifest_entries_are_direct_and_licensed():
    entries = verified_map_library.load_verified_maps()
    assert len(entries) >= 300
    for entry in entries:
        assert entry["url"].lower().split("?", 1)[0].endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
        assert entry["source_page"]
        assert entry["license"]
        assert entry["verified_source"]


def test_institutional_floor_plan_is_not_treated_as_rpg_map():
    prison = {"name": "Dungeon Level Plans San Quentin State Prison HABS"}
    actual = {"name": "Hand Drawn Dungeon Map"}

    assert verified_map_library.is_rpg_play_map(prison) is False
    assert verified_map_library.is_rpg_play_map(actual) is True
