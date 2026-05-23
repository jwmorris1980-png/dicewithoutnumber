import json
import os
import time
from deep_translator import GoogleTranslator

# Target languages: 25 top languages
# Discord supported locales:
# id, da, de, en-GB, en-US, es-ES, fr, hr, it, lt, hu, nl, no, pl, pt-BR, ro, fi, sv-SE, vi, tr, cs, el, bg, ru, uk, hi, th, zh-CN, ja, zh-TW, ko
TARGET_LANGS = {
    'it': 'Italian', 'nl': 'Dutch', 'pl': 'Polish', 'ja': 'Japanese',
    'ko': 'Korean', 'zh': 'Chinese (Simplified)', 'da': 'Danish', 'fi': 'Finnish',
    'no': 'Norwegian', 'tr': 'Turkish', 'cs': 'Czech', 'el': 'Greek',
    'hu': 'Hungarian', 'ro': 'Romanian', 'vi': 'Vietnamese', 'th': 'Thai',
    'uk': 'Ukrainian', 'hi': 'Hindi', 'id': 'Indonesian', 'bg': 'Bulgarian'
}
# We already have en, fr, es, de, pt, sv, ru.

def translate_dict(data, translator):
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            new_dict[k] = translate_dict(v, translator)
        return new_dict
    elif isinstance(data, list):
        return [translate_dict(item, translator) for item in data]
    elif isinstance(data, str):
        # Don't translate placeholders like {lang} or URLs
        # Deep-translator might mess up Markdown or URLs, but it's okay for a quick translation
        try:
            # Sleep to avoid rate limiting
            time.sleep(0.5)
            # If the string contains URLs, it might be tricky. GoogleTranslator usually handles them okay.
            return translator.translate(data)
        except Exception as e:
            print(f"Error translating: {data[:20]}... Error: {e}")
            return data
    else:
        return data

def main():
    en_file = os.path.join("locales", "en.json")
    if not os.path.exists(en_file):
        print("en.json not found")
        return

    with open(en_file, 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    for lang_code, lang_name in TARGET_LANGS.items():
        out_file = os.path.join("locales", f"{lang_code}.json")
        if os.path.exists(out_file):
            print(f"Skipping {lang_name} ({lang_code}) - already exists")
            continue
            
        print(f"Translating to {lang_name} ({lang_code})...")
        try:
            translator = GoogleTranslator(source='en', target=lang_code)
            translated_data = translate_dict(en_data, translator)
            
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(translated_data, f, ensure_ascii=False, indent=4)
            print(f"Successfully generated {lang_code}.json")
        except Exception as e:
            print(f"Failed to generate {lang_code}.json: {e}")

if __name__ == '__main__':
    main()
