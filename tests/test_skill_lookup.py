from cogs.dice import DiceCog


def test_skill_lookup_is_case_insensitive_but_exact():
    skills = {"Notice": 1, "Pilot": 0}

    assert DiceCog._find_exact_named_value(skills, "notice") == ("Notice", 1)
    assert DiceCog._find_exact_named_value(skills, "  PILOT  ") == ("Pilot", 0)


def test_skill_lookup_never_guesses():
    skills = {"Notice": 1, "Pilot": 0}

    assert DiceCog._find_exact_named_value(skills, "noticing") is None
    assert DiceCog._find_exact_named_value({}, "notice") is None
