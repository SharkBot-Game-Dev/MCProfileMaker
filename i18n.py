"""Shared translations for Discord UI and generated cards."""
import json
from pathlib import Path

LANGUAGES = ("ja", "en")
TEXTS = {lang: json.loads((Path(__file__).parent / "langs" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGUAGES}


def locale_language(locale):
    return "ja" if str(locale).startswith("ja") else "en"


def tr(language, key):
    return TEXTS.get(language, TEXTS["ja"]).get(key, TEXTS["ja"][key])
