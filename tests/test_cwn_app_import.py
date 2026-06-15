from types import SimpleNamespace

from cogs.sheets import CharacterSheetCog


def make_cog():
    return CharacterSheetCog(SimpleNamespace())


def test_cwn_app_text_import_preserves_ticket_skills_and_hp():
    text = (
        "Zion Kim [SWN] Level 1 Warrior | Soldier Background "
        "HP: 11/11 | AC: 14 | AB: +1 "
        "ATTRIBUTES STR: 11 (+0) DEX: 15 (+1) "
        "SAVING THROWS Physical: 14+ | Evasion: 14+ | Mental: 14+ "
        "SKILLS Punch-1, Notice-0, Lead-0, Talk-0 "
        "FOCI Unarmed Combatant (Lvl 1), Die Hard (Lvl 1)"
    )

    character, error = make_cog().parse_cwn_app_text(text, "SWN")

    assert error is None
    assert character["name"] == "Zion Kim"
    assert character["hp"] == 11
    assert character["ac"] == 14
    assert character["attack_bonus"] == 1
    assert character["skills"] == {"Punch": 1, "Notice": 0, "Lead": 0, "Talk": 0}


def test_json_import_accepts_hp_container_and_named_skill_list():
    character, error = make_cog()._normalize_character_data(
        {
            "name": "Zion Kim",
            "hitPoints": {"current": 11, "max": 11},
            "skills": [
                {"name": "Punch", "rank": 1},
                {"name": "Notice", "rank": 0},
            ],
        }
    )

    assert error is None
    assert character["hp"] == 11
    assert character["skills"] == {"Punch": 1, "Notice": 0}
