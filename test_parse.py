import re

args = ["😆", "1437265240327983195", "!role", "😍", "1473893626802344007", "!role", "1465361516701155432v", "🥓", "!role", "1437247432307245269", "😮", "!1role", "1474075432658665534", "🎁", "!role", "1473434135857991751", "🐻", "!role", "something", "like", "this"]

emojis = []
ids = []

for arg in args:
    cleaned_arg = re.sub(r'(?<=\d)[a-zA-Z]+$', '', arg)
    if "role" in cleaned_arg.lower():
        continue
    if cleaned_arg.lower() in ['something', 'like', 'this', 'and', 'with']:
        continue
        
    if cleaned_arg.isdigit() and len(cleaned_arg) > 15:
        ids.append(cleaned_arg)
    elif cleaned_arg.startswith("<#") and cleaned_arg.endswith(">"):
        ids.append(cleaned_arg[2:-1])
    else:
        emojis.append(cleaned_arg)

print("Emojis:", emojis)
print("IDs:", ids)
print("Pairs:", list(zip(emojis, ids)))
