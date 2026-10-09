# Tests for book localisation: translated strings, fallbacks, dates, text direction
# and the rendered book template.
import datetime
import json
import logging
import os
import re

import pytest
from jinja2 import Environment, FileSystemLoader

from book_locale import BookLocale, I18N_DIR, read_strings

BOOKS_DIR = os.path.dirname(I18N_DIR)
OCTOBER = datetime.date(2026, 10, 7)


def write_translations(i18n_dir, locale, strings):
    """Write a pulled Transifex file, including the edit_url the pull adds."""
    data = {key: {"string": value, "context": ""} for key, value in strings.items()}
    data['edit_url'] = 'https://www.transifex.com/hisp-uio/docs-full-site/translate/#' + locale
    with open(os.path.join(i18n_dir, f'books_{locale}.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f)


@pytest.fixture
def i18n_dir(tmp_path):
    with open(os.path.join(I18N_DIR, 'strings.json'), encoding='utf-8') as f:
        (tmp_path / 'strings.json').write_text(f.read(), encoding='utf-8')
    return str(tmp_path)


def test_english_uses_source_strings(i18n_dir):
    book_locale = BookLocale('en', i18n_dir)
    assert book_locale.t('cover.author') == 'DHIS2 documentation team'
    assert book_locale.title('DHIS2 User Guide') == 'DHIS2 User Guide'
    assert book_locale.lang == 'en'
    assert book_locale.direction == 'ltr'
    assert book_locale.month_year(OCTOBER) == 'October 2026'


def test_translated_strings_and_titles(i18n_dir):
    write_translations(i18n_dir, 'fr', {
        'cover.author': 'Équipe de documentation DHIS2',
        'DHIS2 User Guide': "Guide de l'utilisateur DHIS2",
    })
    book_locale = BookLocale('fr', i18n_dir)
    assert book_locale.t('cover.author') == 'Équipe de documentation DHIS2'
    assert book_locale.title('DHIS2 User Guide') == "Guide de l'utilisateur DHIS2"
    assert book_locale.month_year(OCTOBER) == 'octobre 2026'


def test_untranslated_strings_fall_back_to_english(i18n_dir):
    write_translations(i18n_dir, 'pt', {'cover.author': ''})
    book_locale = BookLocale('pt', i18n_dir)
    assert book_locale.t('cover.author') == 'DHIS2 documentation team'
    assert book_locale.t('copyright.license_label') == 'License:'
    assert book_locale.title('DHIS2 for Health') == 'DHIS2 for Health'


def test_missing_translations_file_warns_and_uses_english(i18n_dir, caplog):
    with caplog.at_level(logging.WARNING):
        book_locale = BookLocale('cs', i18n_dir)
    assert book_locale.t('cover.author') == 'DHIS2 documentation team'
    assert len(caplog.records) == 1
    assert caplog.records[0].getMessage() == (
        f"No book translations at {os.path.join(i18n_dir, 'books_cs.json')}; using English strings for 'cs'.")


def test_unknown_string_key_fails(i18n_dir):
    with pytest.raises(KeyError):
        BookLocale('en', i18n_dir).t('cover.missing')


@pytest.mark.parametrize('locale, lang, direction, month_year', [
    ('es_419', 'es-419', 'ltr', 'octubre de 2026'),
    ('cs', 'cs', 'ltr', 'říjen 2026'),
    ('zh', 'zh', 'ltr', '2026年10月'),
    ('ar', 'ar', 'rtl', 'أكتوبر 2026'),
])
def test_locale_conventions(i18n_dir, caplog, locale, lang, direction, month_year):
    book_locale = BookLocale(locale, i18n_dir)
    assert book_locale.lang == lang
    assert book_locale.direction == direction
    assert book_locale.month_year(OCTOBER) == month_year
    assert len(caplog.records) == 1


def test_read_strings_skips_edit_url_and_empty_strings(i18n_dir):
    write_translations(i18n_dir, 'fr', {'cover.author': 'Équipe', 'copyright.holder': ''})
    assert read_strings(os.path.join(i18n_dir, 'books_fr.json')) == {'cover.author': 'Équipe'}


def test_every_template_string_has_an_english_source():
    source = read_strings(os.path.join(I18N_DIR, 'strings.json'))
    templates_dir = os.path.join(BOOKS_DIR, 'templates')
    used = set()
    for name in os.listdir(templates_dir):
        with open(os.path.join(templates_dir, name), encoding='utf-8') as f:
            used |= set(re.findall(r"\bt\('([^']+)'\)", f.read()))
    assert used
    assert used <= set(source)


def render_book(book_locale):
    env = Environment(loader=FileSystemLoader(BOOKS_DIR))
    return env.get_template('templates/book.html').render(
        title=book_locale.title('DHIS2 User Guide'), cover='cover.jpg', toc_section='', inner_html='',
        currentDocIntro=None, month_year=book_locale.month_year(OCTOBER), year=2026,
        lang=book_locale.lang, direction=book_locale.direction, t=book_locale.t)


def test_rendered_book_is_localised_and_keeps_english_legal_text(i18n_dir):
    write_translations(i18n_dir, 'ar', {
        'cover.author': 'فريق توثيق DHIS2',
        'copyright.warranty_label': 'الضمان:',
        'DHIS2 User Guide': 'دليل مستخدم DHIS2',
    })
    html = render_book(BookLocale('ar', i18n_dir))
    assert '<html lang="ar" class="no-js">' in html
    assert '<body>' in html
    assert '<link rel="stylesheet" href="resources/css/books-rtl.css">' in html
    assert html.count('dir="rtl"') == 3
    assert '<header>دليل مستخدم DHIS2</header>' in html
    assert '<p>فريق توثيق DHIS2<br>أكتوبر 2026</p>' in html
    assert '<strong>الضمان:</strong> THIS DOCUMENT IS PROVIDED BY THE AUTHORS' in html
    assert '<strong>License:</strong> Permission is granted' in html


def test_rendered_english_book(i18n_dir):
    html = render_book(BookLocale('en', i18n_dir))
    assert '<html lang="en" class="no-js">' in html
    assert 'books-rtl.css' not in html
    assert html.count('dir="ltr"') == 3
    assert '<p>DHIS2 documentation team<br>October 2026</p>' in html
    assert '<p class="author">DHIS2 Core Team</p>' in html
