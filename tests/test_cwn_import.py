import csv
import io
import re

def fetch_and_parse_sheet(text: str):
    # Simplified version of the logic in sheets.py for testing
    reader = csv.reader(io.StringIO(text))
    grid = list(reader)
    
    char_data = {
        "name": "Unknown",
        "class": "Unknown",
        "level": 1,
        "hp": 1,
        "ac": 10,
        "attack_bonus": 0,
        "initiative": 0,
        "saves": {"physical": 15, "mental": 15, "evasion": 15, "luck": 15},
        "attributes": {},
        "skills": {},
        "weapons": [],
        "xp": 0,
        "system": "SWN"
    }
    
    header_text = "".join(["".join(row) for row in grid[:5]]).upper()
    if "CITIES WITHOUT NUMBER" in header_text or "CWN" in header_text:
        char_data["system"] = "CWN"

    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            val = cell.strip()
            if not val:
                continue
            
            if val in ["Name", "Character Name"] and c+1 < len(row) and grid[r][c+1]:
                char_data["name"] = grid[r][c+1]
            elif val == "Class" and c+1 < len(row) and grid[r][c+1]:
                char_data["class"] = grid[r][c+1]
            elif val == "Level" and c+1 < len(row) and grid[r][c+1]:
                try: char_data["level"] = int(grid[r][c+1])
                except: pass
            elif val == "Species":
                for offset in [1, 2, 4]:
                    if c+offset < len(row) and grid[r][c+offset].strip():
                        char_data["species"] = grid[r][c+offset].strip()
                        break
            elif val == "Homeworld":
                for offset in [1, 2, 4]:
                    if c+offset < len(row) and grid[r][c+offset].strip():
                        char_data["homeworld"] = grid[r][c+offset].strip()
                        break
                
            elif val in ["Max HP", "Current HP", "HP Rolled", "HP"]:
                if char_data.get("hp", 1) > 1 and "Rolled" in val:
                    continue
                for offset in [1, 2, 4, 6]:
                    if c+offset < len(row) and grid[r][c+offset]:
                        try:
                            h_val = int(grid[r][c+offset])
                            if h_val > 0:
                                char_data["hp"] = h_val
                                break
                        except: pass
            elif val in ["AC", "Ranged AC", "Melee AC", "Armor Class"]:
                for offset in [1, 2, 4]:
                    if c+offset < len(row) and grid[r][c+offset]:
                        try:
                            ac_val = int(grid[r][c+offset])
                            if ac_val > 5:
                                char_data["ac"] = ac_val
                                break
                        except: pass
            elif val in ["Attack Bonus", "AB"]:
                for offset in [1, 2, 4]:
                    if c+offset < len(row) and grid[r][c+offset]:
                        try:
                            ab_str = grid[r][c+offset].replace("+", "")
                            char_data["attack_bonus"] = int(ab_str or "0")
                            break
                        except: pass
                 
            elif val in ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]:
                 attr_key = val.lower()[:3]
                 for offset in [7, 8, 9, 4, 2]:
                     if c+offset < len(row) and grid[r][c+offset]:
                         try:
                             v_str = grid[r][c+offset].replace("+", "").strip()
                             if not v_str: continue
                             v = int(v_str)
                             if -5 <= v <= 5:
                                 char_data["attributes"][attr_key] = v
                                 break
                         except: pass
                      
            elif val in ["Physical", "Mental", "Evasion", "Luck", "Physical Save", "Mental Save", "Evasion Save", "Luck Save"]:
                 save_key = val.lower().replace(" save", "")
                 for offset in [1, 2, 3, 4, 12, 14, 16]:
                     if c+offset < len(row) and grid[r][c+offset]:
                         try:
                             s_str = grid[r][c+offset].replace("+", "").strip()
                             if not s_str: continue
                             char_data["saves"][save_key] = int(s_str)
                             break
                         except: pass
                      
            elif val == "Initiative":
                 for offset in [1, 2, 4]:
                     if c+offset < len(row) and grid[r][c+offset]:
                         try:
                             char_data["initiative"] = int(grid[r][c+offset])
                             break
                         except: pass
            
            elif val in ["Administer", "Connect", "Exert", "Fix", "Heal", "Know", "Lead", "Notice", "Perform", "Pilot", "Program", "Magic", "Shoot", "Sneak", "Stab", "Pray", "Talk", "Trade", "Work", "Survival", "Cast"]:
                 skill_name = val.lower()
                 if skill_name == "survival": skill_name = "survive"
                 for offset in [8, 9, 10, 1, 2]:
                     if c+offset < len(row) and grid[r][c+offset]:
                         try:
                             s_val = int(grid[r][c+offset])
                             if -1 <= s_val <= 5:
                                 char_data["skills"][skill_name] = s_val
                                 break
                         except: pass
                      
            elif val in ["Weapons", "Ranged Weapons", "Melee Weapons"] and c+2 < len(row):
                for w_row in range(r+1, min(r+12, len(grid))):
                    if c >= len(grid[w_row]):
                        continue
                    w_name = grid[w_row][c]
                    if not w_name or w_name in ["Abilities", "Ability Description", "Foci", "Equipment", "Skill Points"]: 
                        break 
                    w_dmg = ""
                    w_tohit = 0
                    for off in [9, 8, 7, 5, 2]:
                        if c+off < len(grid[w_row]):
                            cell_val = grid[w_row][c+off].lower()
                            if "d" in cell_val and any(char.isdigit() for char in cell_val):
                                w_dmg = grid[w_row][c+off]
                                for th_off in [2, 3, 4, 1]:
                                    if c+off-th_off >= 0:
                                        try:
                                            th_str = grid[w_row][c+off-th_off].replace("+", "").strip()
                                            if th_str:
                                                w_tohit = int(th_str)
                                                break
                                        except: pass
                                break
                    if w_name and w_dmg:
                        char_data["weapons"].append({
                            "name": w_name,
                            "to_hit": w_tohit,
                            "damage": w_dmg
                        })

    if char_data["name"] == "Unknown" and len(grid) > 4:
        if grid[0][0].startswith("CWN"):
            char_data["name"] = grid[0][0].replace("CWN", "").strip()
        elif grid[3][1]:
            char_data["name"] = grid[3][1].strip()

    return char_data

def test_import():
    with open('c:/Users/Yeyian PC/OneDrive/Desktop/DICEwithoutNumber/tests/gid0.csv', 'r', encoding='utf-8') as f:
        text = f.read()
    
    data = fetch_and_parse_sheet(text)
    print(f"System: {data['system']}")
    print(f"Name: {data['name']}")
    print(f"Level: {data['level']}")
    print(f"HP: {data['hp']}")
    print(f"AC: {data['ac']}")
    print(f"Attack Bonus: {data['attack_bonus']}")
    print(f"Attributes: {data['attributes']}")
    print(f"Saves: {data['saves']}")
    print(f"Skills: {data['skills']}")
    print(f"Weapons: {data['weapons']}")
    print(f"Species: {data.get('species')}")
    print(f"Homeworld: {data.get('homeworld')}")

if __name__ == "__main__":
    test_import()
