import unicodedata

args = ["😆", "1437265240327983195", "!role\u200b", "😍", "1473893626802344007", "role", "1465361516701155432v", "🥓", "!", "1437247432307245269", "😮", "!1role", "1474075432658665534", "🎁", "1473434135857991751", "🐻", "something", "like", "this", "❤️", "1️⃣", "🇦", "🇦🇷", "!role\u200e"]

emojis = []
for arg in args:
    cleaned_for_emoji = ""
    for c in arg:
        cat = unicodedata.category(c)
        if not (cat.startswith('L') or cat.startswith('N') or cat.startswith('P') or cat.startswith('Z') or cat.startswith('C')):
            cleaned_for_emoji += c
    if cleaned_for_emoji:
        emojis.append(arg)
        
print("Emojis:", [e.encode('unicode_escape').decode() for e in emojis])
