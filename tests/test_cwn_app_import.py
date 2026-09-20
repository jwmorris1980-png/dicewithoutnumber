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
    assert character["hp_max"] == 11
    assert character["ac"] == 14
    assert character["attack_bonus"] == 1
    assert character["system"] == "SWN"
    assert character["class"] == "Warrior"
    assert character["skills"] == {"Punch": 1, "Notice": 0, "Lead": 0, "Talk": 0}
    assert character["attributes"]["dexterity"] == 1
    assert character["attribute_scores"]["dexterity"] == 15
    assert "Unarmed Combatant (Lvl 1)" in character["foci"]


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


def test_v08_json_import_uses_class_skill_ids_and_attribute_scores():
    character, error = make_cog()._normalize_character_data(
        {
            "id": "char-1",
            "name": "Rey Chen",
            "classId": "warrior",
            "backgroundId": "soldier",
            "gameSystem": "swn",
            "level": 2,
            "hitPointsCurrent": 14,
            "hitPointsMax": 16,
            "attackBonus": 2,
            "armorClass": 15,
            "meleeArmorClass": 14,
            "systemStrainCurrent": 1,
            "systemStrainMax": 14,
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-02T00:00:00Z",
            "attributes": {
                "strength": 14,
                "dexterity": 11,
                "constitution": 16,
                "intelligence": 7,
                "wisdom": 10,
                "charisma": 8,
            },
            "savingThrows": {"physical": 12, "evasion": 13, "mental": 14},
            "skills": [
                {"skillId": "punch", "rank": 1},
                {"skillId": "notice", "rank": 0},
                {"skillId": "shoot", "rank": 1},
            ],
            "foci": [
                {"focusId": "unarmed-combatant", "level": 1},
                {"focusId": "die-hard", "level": 1},
            ],
            "inventory": [
                {"itemId": "laser-pistol", "quantity": 1, "location": "readied"},
                {"itemId": "type-a-cells", "quantity": 2, "location": "stowed"},
            ],
            "equipment": ["Vacc Suit"],
            "conditions": [],
            "credits": 250,
            "experience": 3,
            "journal": {"sessionLog": [], "npcs": [], "quests": [], "generalNotes": ""},
        }
    )

    assert error is None
    assert character["name"] == "Rey Chen"
    assert character["system"] == "SWN"
    assert character["class"] == "Warrior"
    assert character["background"] == "Soldier"
    assert character["hp"] == 14
    assert character["hp_max"] == 16
    assert character["ac"] == 15
    assert character["melee_ac"] == 14
    assert character["attack_bonus"] == 2
    assert character["attributes"]["strength"] == 1
    assert character["attribute_scores"]["strength"] == 14
    assert character["attributes"]["intelligence"] == -1
    assert character["skills"] == {"Punch": 1, "Notice": 0, "Shoot": 1}
    assert character["foci"] == ["Unarmed Combatant (Lvl 1)", "Die Hard (Lvl 1)"]
    assert character["strain"] == "1/14"
    assert any(weapon["name"] == "Laser Pistol" for weapon in character["weapons"])
    laser = next(weapon for weapon in character["weapons"] if weapon["name"] == "Laser Pistol")
    assert laser["damage"] == "1d6"
    assert "Vacc Suit" in character["equipment"]


def test_cwn_json_import_reads_edges_and_inventory_weapons():
    character, error = make_cog()._normalize_character_data(
        {
            "name": "Nyx",
            "classId": "hacker",
            "gameSystem": "cwn",
            "level": 1,
            "hitPointsCurrent": 8,
            "hitPointsMax": 8,
            "attackBonus": 0,
            "armorClass": 13,
            "attributes": {"strength": 10, "dexterity": 14, "constitution": 12, "intelligence": 16, "wisdom": 9, "charisma": 11},
            "skills": [{"skillId": "program", "rank": 1}, {"skillId": "hack", "rank": 0}],
            "selectedEdges": [{"edgeId": "ghost"}, "on-target"],
            "inventory": [
                {"itemId": "heavy-pistol", "quantity": 1, "location": "readied", "customDamage": "1d8"},
            ],
        }
    )

    assert error is None
    assert character["system"] == "CWN"
    assert character["class"] == "Hacker"
    assert character["attributes"]["dexterity"] == 1
    assert "Ghost" in character["edges"]
    assert "On Target" in character["edges"]
    assert character["weapons"][0]["name"] == "Heavy Pistol"
    assert character["weapons"][0]["damage"] == "1d8"


def test_google_sheet_modifiers_are_not_treated_as_scores():
    character, error = make_cog()._normalize_character_data(
        {
            "name": "Sheet Hero",
            "attributes": {"strength": 1, "dexterity": 0, "constitution": -1, "intelligence": 0, "wisdom": 0, "charisma": 2},
            "hp": 10,
        }
    )

    assert error is None
    assert character["attributes"]["strength"] == 1
    assert character["attributes"]["constitution"] == -1
    assert character["attributes"]["charisma"] == 2
    assert character["attribute_scores"] == {}


def test_copy_text_is_detected_for_auto_import():
    cog = make_cog()
    text = "Zion Kim [SWN] Level 1 Warrior HP: 11/11 SKILLS Punch-1"
    assert cog._looks_like_cwn_app_text(text) is True
    assert cog._looks_like_cwn_app_text("I have 11 HP from a fight") is False
    assert cog._is_cwn_app_url("https://characterswithoutnumber.app/c/abc123") is True
    assert cog._is_cwn_app_url("https://docs.google.com/spreadsheets/d/abc") is False


def test_share_page_help_mentions_json_and_copy_text():
    help_text = make_cog()._cwn_app_share_help()
    assert "Export → JSON" in help_text
    assert "Copy Text" in help_text


def test_hp_display_uses_current_and_max():
    cog = make_cog()
    assert cog._hp_display({"hp": 14, "hp_max": 16}) == "14/16"
    assert "14 (+1)" in cog._attribute_display({"attributes": {"strength": 1}, "attribute_scores": {"strength": 14}})
