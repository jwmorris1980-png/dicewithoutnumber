import json
import os
import re

def extract_foci(index_path: str, foci_path: str):
    print("Starting Foci extraction...")
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            rules_index = json.load(f)
    except Exception as e:
        print(f"Error loading index: {e}")
        return

    try:
        with open(foci_path, 'r', encoding='utf-8') as f:
            existing_foci = json.load(f)
    except Exception:
        existing_foci = []

    existing_names = {f["name"].lower() for f in existing_foci}
    new_foci = []

    # Heuristic for Kevin Crawford games: Foci are often formatted as:
    # FOCUS NAME
    # [Flavor text/description]
    # Level 1: [Effect]
    # Level 2: [Effect]
    
    # We look for "Level 1:" to anchor our search in the raw text
    
    for page in rules_index:
        content = page["content"]
        
        # Split page by double-spaces or newlines (though we stripped most newlines)
        # Actually, PyMuPDF get_text() retains some structure. In our clean_text we turned
        # multiple spaces/newlines into a single space. Let's look for the pattern directly.
        
        # Find all occurrences of "Level 1:"
        matches = list(re.finditer(r'(?i)Level 1:', content))
        
        for m in matches:
            start_idx = m.start()
            
            # The focus name and description usually precede "Level 1:"
            # Let's take the ~200 characters before it and try to find a Title Case string
            pre_text = content[max(0, start_idx-250):start_idx].strip()
            
            # Very crude heuristic: The last full sentence or phrase before "Level 1" is the description.
            # The capitalized word(s) before that is the Focus Name.
            
            # Let's split by sentence boundaries
            parts = re.split(r'(?<=[.!?])\s+', pre_text)
            if len(parts) >= 2:
                description = parts[-1].strip()
                # Attempt to guess the name from the previous part
                name_candidate = parts[-2].strip().split()[-3:] # take last 3 words just in case
                name = " ".join([w for w in name_candidate if w[0].isupper()])
            else:
                continue
                
            if not name or len(name) < 3:
                continue
                
            # Now find Level 2 if it exists
            level1_end = content.find("Level 2:", start_idx)
            if level1_end == -1:
                 # maybe there is no level 2 on this page, or it's a 1-level focus
                 level1_text = content[start_idx:start_idx+150].strip()
            else:
                 level1_text = content[start_idx:level1_end].strip()
                 level2_text = content[level1_end:level1_end+150].strip()
                 # A real implementation would bound this better, but this is a rough extract
                 level1_text += "\n" + level2_text

            full_desc = f"{description}\n{level1_text}"
            
            if name.lower() not in existing_names:
                new_foci.append({
                    "name": name,
                    "level": 1,
                    "description": full_desc,
                    "source_book": page["book"]
                })
                existing_names.add(name.lower())

    # Save results
    if new_foci:
        existing_foci.extend(new_foci)
        with open(foci_path, 'w', encoding='utf-8') as f:
            json.dump(existing_foci, f, indent=4)
        print(f"Extracted {len(new_foci)} potential new Foci. (Note: Output will be messy and require manual review)")
    else:
        print("No new Foci patterns confidently found.")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    data_directory = os.path.join(project_dir, 'data')
    
    extract_foci(os.path.join(data_directory, 'rules_index.json'), os.path.join(data_directory, 'foci.json'))
