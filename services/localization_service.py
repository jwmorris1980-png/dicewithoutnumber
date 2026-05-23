import json
import os
import logging

logger = logging.getLogger('discord')

class LocalizationService:
    def __init__(self, locales_dir="locales"):
        self.locales_dir = locales_dir
        self.translations = {}
        self.default_locale = "en"
        self._load_locales()

    def _load_locales(self):
        if not os.path.exists(self.locales_dir):
            os.makedirs(self.locales_dir)
            # Create a dummy en.json if it doesn't exist
            with open(os.path.join(self.locales_dir, "en.json"), "w") as f:
                json.dump({"test": "Success"}, f)

        for filename in os.listdir(self.locales_dir):
            if filename.endswith(".json"):
                locale = filename[:-5]
                try:
                    with open(os.path.join(self.locales_dir, filename), "r", encoding="utf-8") as f:
                        self.translations[locale] = json.load(f)
                    logger.info(f"Loaded locale: {locale}")
                except Exception as e:
                    logger.error(f"Failed to load locale {locale}: {e}")

    def translate(self, key, locale="en", **kwargs):
        # Fallback to default if locale not found
        lang_data = self.translations.get(locale, self.translations.get(self.default_locale, {}))
        
        # Nested key support (e.g. "intro.swn.title")
        keys = key.split(".")
        value = lang_data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = None
                break
        
        # Final fallback to English if key missing in target locale
        if value is None and locale != self.default_locale:
            return self.translate(key, self.default_locale, **kwargs)
        
        if value is None:
            return key # Return key name as last resort

        try:
            return value.format(**kwargs)
        except Exception as e:
            logger.error(f"Translation formatting error for {key}: {e}")
            return value
