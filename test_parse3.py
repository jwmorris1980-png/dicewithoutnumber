import re

args = ["😆", "1437265240327983195", "!role\u200b", "😍", "1473893626802344007", "role", "1465361516701155432v", "🥓", "!", "1437247432307245269", "😮", "!1role", "1474075432658665534", "🎁", "1473434135857991751", "🐻", "something", "like", "this", "❤️", "1️⃣", "🇦", "🇦🇷"]

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
        
    # Heuristic: strip all standard ASCII, punctuation, and common zero-width chars.
    # If anything remains, it's an emoji (or foreign language text, which shouldn't be here anyway).
    cleaned_for_emoji = re.sub(r'[a-zA-Z0-9\!\@\#\$\%\^\&\*\(\)\-\_\+\=\[\]\{\}\|;:\'\",\.\<\>\/\?\s\u200b\u200c\u200d\uFE0F]', '', arg)
    if cleaned_for_emoji:
        emojis.append(arg)

print("Emojis:", [e.encode('unicode_escape').decode() for e in emojis])
print("IDs:", ids)
