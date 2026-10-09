# Localised strings, dates and text direction for the PDF books.
# Reads the Transifex translations pulled into i18n/, falling back to the English source strings.
import json
import logging
import os

from babel.dates import format_skeleton

I18N_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'i18n')
RTL_LANGUAGES = {'ar'}


def read_strings(path):
    """Read a Transifex STRUCTURED_JSON file into a {key: string} dict.

    Entries that are not translation units (such as the edit_url added on pull)
    and empty (untranslated) strings are skipped.
    """
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {key: value['string'] for key, value in data.items()
            if isinstance(value, dict) and value.get('string')}


class BookLocale:

    def __init__(self, locale='en', i18n_dir=I18N_DIR):
        self.locale = locale
        self.source = read_strings(os.path.join(i18n_dir, 'strings.json'))
        self.translations = {}
        if locale != 'en':
            path = os.path.join(i18n_dir, f'books_{locale}.json')
            if os.path.exists(path):
                self.translations = read_strings(path)
            else:
                logging.warning(f"No book translations at {path}; using English strings for '{locale}'.")

    @property
    def lang(self):
        """The locale as a BCP 47 tag for the html lang attribute (es_419 -> es-419)."""
        return self.locale.replace('_', '-')

    @property
    def direction(self):
        return 'rtl' if self.locale.split('_')[0] in RTL_LANGUAGES else 'ltr'

    def t(self, key):
        """Translate a book UI string by its key in strings.json."""
        return self.translations.get(key) or self.source[key]

    def title(self, english_title):
        """Translate a book title from docs.yml, which is keyed by its English text."""
        return self.translations.get(english_title, english_title)

    def month_year(self, date):
        """Month and year in the locale's own order and month form, e.g. "October 2026", "2026年10月"."""
        return format_skeleton('yMMMM', date, locale=self.locale)
