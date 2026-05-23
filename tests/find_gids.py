import requests

doc_id = '10DZbjfJymwiYdmYJsJ92x-a390NzL67U8wm_hk1RP80'

# Try a range of GIDs
for gid in range(0, 10):
    url = f'https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid={gid}'
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            first_line = response.text.split('\n')[0]
            print(f"GID {gid}: {first_line[:100]}")
    except:
        pass

# Also try some large common GIDs
common_gids = [1667104353, 2068994519, 142340332, 743452980]
for gid in common_gids:
    url = f'https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid={gid}'
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            first_line = response.text.split('\n')[0]
            print(f"GID {gid}: {first_line[:100]}")
    except:
        pass
