from services.focused_rpg_map_search import expand_map_query, focused_map_search, score_map_entry


def test_query_expansion_adds_rpg_map_terms():
    terms = expand_map_query("find map forest")

    assert "forest" in terms
    assert "woods" in terms
    assert "battlemap" in terms
    assert "vtt" in terms


def test_scoring_prefers_battlemaps_over_reference_maps():
    terms = expand_map_query("city")
    battlemap = {
        "id": "good",
        "type": "map",
        "name": "City Battlemap",
        "tags": ["city", "battlemap", "vtt"],
        "url": "https://2minutetabletop.com/city-battlemap.jpg",
        "source_page": "https://2minutetabletop.com/maps/",
    }
    reference = {
        "id": "bad",
        "type": "map",
        "name": "City tourist reference map",
        "tags": ["city", "map"],
        "url": "https://2minutetabletop.com/city-reference.jpg",
        "source_page": "https://2minutetabletop.com/maps/",
    }

    assert score_map_entry(battlemap, terms) > score_map_entry(reference, terms)


def test_focused_search_finds_existing_color_map():
    result = focused_map_search("cyberpunk city")

    assert result
    assert "Cyberpunk" in result[0]["name"]
    assert result[0]["url"].startswith("https://")


def test_focused_search_finds_forest_battlemap():
    result = focused_map_search("forest")

    assert result
    assert "forest" in " ".join(result[0]["tags"]).lower()
    assert "battlemap" in " ".join(result[0]["tags"]).lower()


def test_focused_search_finds_town_and_village_battlemaps():
    town = focused_map_search("town")
    village = focused_map_search("village")

    assert town
    assert "town" in " ".join(town[0]["tags"]).lower()
    assert village
    assert "village" in " ".join(village[0]["tags"]).lower()
