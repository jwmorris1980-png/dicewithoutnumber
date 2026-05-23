import requests

url = "https://docs.google.com/spreadsheets/d/10DZbjfJymwiYdmYJsJ92x-a390NzL67U8wm_hk1RP80/export?format=csv&gid=0"
response = requests.get(url)
if response.status_code == 200:
    lines = response.text.split('\n')
    for i, line in enumerate(lines[:150]):
        print(f"{i:03}: {line}")
else:
    print(f"Error: {response.status_code}")
