args = ["😆", "1437265240327983195", "!role", "😍", "1473893626802344007", "!role", "1465361516701155432v", "🥓", "!role", "1437247432307245269", "😮", "!1role", "1474075432658665534", "🎁", "!role", "1473434135857991751", "🐻", "!role", "something", "like", "this", "❤️", "1️⃣", "🇦"]

import re

emojis = []
ids = []

for arg in args:
    if arg.startswith("<:") or arg.startswith("<a:"):
        emojis.append(arg)
        continue
    if arg.startswith("<#") and arg.endswith(">"):
        ids.append(arg[2:-1])
        continue
        
    cleaned_arg = re.sub(r'(?<=\d)[a-zA-Z]+$', '', arg)
    if cleaned_arg.isdigit() and len(cleaned_arg) > 15:
        ids.append(cleaned_arg)
        continue
        
    if any(ord(c) > 255 for c in arg):
        emojis.append(arg)

print(len(emojis), "Emojis:", [e.encode('unicode_escape').decode() for e in emojis])
print(len(ids), "IDs:", ids)
