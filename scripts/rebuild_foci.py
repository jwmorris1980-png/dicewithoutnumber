import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RULES_INDEX = ROOT / "data" / "rules_index.json"
FOCI_JSON = ROOT / "data" / "foci.json"


SOURCE_SECTIONS = [
    {
        "book": "Stars WN",
        "pages": [24, 25, 26, 27],
        "names": [
            "Alert",
            "Armsman",
            "Assassin",
            "Authority",
            "Close Combatant",
            "Connected",
            "Die Hard",
            "Diplomat",
            "Gunslinger",
            "Hacker",
            "Healer",
            "Henchkeeper",
            "Ironhide",
            "Psychic Training",
            "Savage Fray",
            "Shocking Assault",
            "Sniper",
            "Specialist",
            "Star Captain",
            "Starfarer",
            "Tinker",
            "Unarmed Combatant",
            "Unique Gift",
            "Wanderer",
            "Wild Psychic Talent",
        ],
    },
    {
        "book": "Stars WN",
        "pages": [276, 277],
        "category": "Arcane",
        "names": [
            "Armored Technique",
            "Cross-Disciplinary Study",
            "Imprinted Spell",
            "Initiate of Healing",
            "Limited Study",
            "Petty Sorceries",
            "Psychic Synergy",
            "Savage Sorcery",
            "Vast Erudition",
            "War Caster",
        ],
    },
    {
        "book": "Worlds WN",
        "pages": [25, 26, 27, 28, 29, 30],
        "names": [
            "Alert",
            "Armored Magic",
            "Armsmaster",
            "Artisan",
            "Assassin",
            "Authority",
            "Close Combatant",
            "Connected",
            "Cultured",
            "Die Hard",
            "Deadeye",
            "Dealmaker",
            "Developed Attribute",
            "Diplomatic Grace",
            "Gifted Chirurgeon",
            "Henchkeeper",
            "Impervious Defense",
            "Impostor",
            "Lucky",
            "Nullifier",
            "Poisoner",
            "Polymath",
            "Rider",
            "Shocking Assault",
            "Sniper's Eye",
            "Specialist",
            "Spirit Familiar",
            "Trapmaster",
            "Unarmed Combatant",
            "Unique Gift",
            "Valiant Defender",
            "Well Met",
            "Whirlwind Assault",
            "Xenoblooded",
        ],
        "patterns": {"Sniper's Eye": "Snipers Eye"},
    },
    {
        "book": "Worlds WN",
        "pages": [314],
        "category": "Origin",
        "names": [
            "Dwarves",
            "Elves, Civilized",
            "Elves, Half-Elves",
            "Elves, Forest",
            "Halflings",
            "Gnomes",
            "Goblins, Tinker",
            "Goblins, Savage",
            "Lizardmen",
            "Orcs",
        ],
    },
    {
        "book": "Worlds WN",
        "pages": [315],
        "category": "Origin",
        "names": ["Origin Focus: Dwarf"],
        "patterns": {"Origin Focus: Dwarf": "Origin Focus: Dwarf"},
    },
    {
        "book": "Cities WN",
        "pages": [23, 24, 25, 26, 27],
        "names": [
            "Ace Driver",
            "Alert",
            "All Natural",
            "Armsmaster",
            "Assassin",
            "Authority",
            "Close Combatant",
            "Cyberdoc",
            "Deadeye",
            "Diplomat",
            "Drone Pilot",
            "Expert Programmer",
            "Healer",
            "Henchkeeper",
            "Many Faces",
            "Pop Idol",
            "Roamer",
            "Safe Haven",
            "Shocking Assault",
            "Sniper's Eye",
            "Specialist",
            "Tinker",
            "Unarmed Combatant",
            "Unique Gift",
            "Unregistered",
            "Whirlwind Assault",
        ],
        "patterns": {"Sniper's Eye": "Snipers Eye"},
    },
]


def load_pages():
    with RULES_INDEX.open(encoding="utf-8") as f:
        pages = json.load(f)
    by_book_page = {(page["book"], page["page"]): page["content"] for page in pages}
    return by_book_page


def clean_text(value):
    value = value.replace("\x08", " ")
    value = re.sub(r"\bArcane Foci\s+\d+\b", " ", value)
    value = re.sub(r"\bFoci\s+\d+\b", " ", value)
    value = re.sub(r"\b\d+\s+Foci\b", " ", value)
    value = re.sub(r"\b\d+\s+Focus List\b", " ", value)
    value = re.sub(r"(\w)-\s+(\w)", r"\1\2", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def find_name_positions(text, section):
    positions = []
    patterns = section.get("patterns", {})
    cursor = 0

    for name in section["names"]:
        pattern_name = patterns.get(name, name)
        pattern = re.compile(rf"(?:\b\d+\s+)?(?<!\w){re.escape(pattern_name)}(?!\w)")
        match = pattern.search(text, cursor)
        if not match:
            raise ValueError(f"Could not find {name!r} in {section['book']} pages {section['pages']}")
        name_start = match.start()
        name_end = match.end()
        number_prefix = re.match(r"\d+\s+", text[name_start:name_end])
        if number_prefix:
            name_start += number_prefix.end()
        positions.append((name, name_start, name_end))
        cursor = match.end()

    return positions


def extract_section(section, by_book_page):
    raw_text = " ".join(by_book_page[(section["book"], page)] for page in section["pages"])
    text = clean_text(raw_text)
    positions = find_name_positions(text, section)
    records = []

    for index, (name, start, name_end) in enumerate(positions):
        end = positions[index + 1][1] if index + 1 < len(positions) else len(text)
        body = clean_text(text[name_end:end])
        body = re.sub(r"\s+\d{1,3}$", "", body).strip()

        records.append(
            {
                "name": name,
                "level": 1,
                "description": body,
                "source_book": section["book"],
                "source_pages": section["pages"],
                **({"category": section["category"]} if "category" in section else {}),
            }
        )

    return records


def rebuild():
    by_book_page = load_pages()
    records = []

    for section in SOURCE_SECTIONS:
        records.extend(extract_section(section, by_book_page))

    with FOCI_JSON.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=4, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {len(records)} foci to {FOCI_JSON}")


if __name__ == "__main__":
    rebuild()
