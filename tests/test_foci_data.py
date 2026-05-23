import json
from pathlib import Path

from cogs.compendium import CompendiumCog
from game_data import CWN_FOCI, SWN_FOCI, WWN_FOCI


FOCI_PATH = Path(__file__).resolve().parents[1] / "data" / "foci.json"


def load_foci():
    return json.loads(FOCI_PATH.read_text(encoding="utf-8"))


def test_foci_data_has_expected_books_and_no_bad_extraction_names():
    foci = load_foci()
    names = {focus["name"] for focus in foci}
    bad_names = {"PCs.", "Constitution", "Effort.", "Shoot", "Contact", "Hell."}

    assert len(foci) == 106
    assert not names.intersection(bad_names)
    assert {"Stars WN", "Worlds WN", "Cities WN"} <= {focus["source_book"] for focus in foci}


def test_all_foci_have_complete_level_text():
    for focus in load_foci():
        description = focus["description"]
        if focus["name"] != "Unique Gift":
            assert "Level 1:" in description
        assert not description.endswith(("Foci", "Focus List"))
        assert not description[-1].isdigit()


def test_validation_lists_match_compendium_names():
    foci = load_foci()
    by_book = {
        "Stars WN": {focus["name"] for focus in foci if focus["source_book"] == "Stars WN"},
        "Worlds WN": {focus["name"] for focus in foci if focus["source_book"] == "Worlds WN"},
        "Cities WN": {focus["name"] for focus in foci if focus["source_book"] == "Cities WN"},
    }

    assert set(SWN_FOCI) == by_book["Stars WN"]
    assert set(WWN_FOCI) == by_book["Worlds WN"]
    assert set(CWN_FOCI) == by_book["Cities WN"]


def test_compendium_can_disambiguate_duplicate_focus_names():
    cog = CompendiumCog(bot=None)

    stars_alert = cog._find_focus("Stars WN||Alert")
    cities_alert = cog._find_focus("Cities WN||Alert")

    assert stars_alert["source_book"] == "Stars WN"
    assert cities_alert["source_book"] == "Cities WN"
    assert "Stars WN" in cog._foci_label(stars_alert)
    assert "Cities WN" in cog._foci_label(cities_alert)
