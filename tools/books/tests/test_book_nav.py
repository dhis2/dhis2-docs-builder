# Tests that book nav handling works on localised sites, where nav titles are translated:
# site sections and non-book pages are recognised by their paths, not their titles.
import os

import pytest

import book_builder
from book_builder import navReader

BASE = './target/en/'

NAV_PAGE = """<html><body>
<nav class="md-nav md-nav--primary" aria-label="Navigation">
  <ul class="md-nav__list">
    <li><a href="../home.html">Accueil</a></li>
    <li><a href="../terms-of-use.html">Conditions d'utilisation</a></li>
    <li>
      <label>Utilisation</label><a href="OVERVIEW.html">Utilisation</a>
      <ul class="md-nav__list">
        <li><a href="OVERVIEW.html">Utilisation</a></li>
        <li><a href="collecting-data.html">Collecte des données</a></li>
      </ul>
    </li>
  </ul>
</nav>
<article><div><p>Contenu</p></div></article>
</body></html>"""


def page(text):
    return f'<html><body><article><div><p>{text}</p></div></article></body></html>'


@pytest.fixture
def localised_site(tmp_path, monkeypatch):
    """A rendered site with French nav titles, with the builder running from its root."""
    site = tmp_path / 'target' / 'en'
    (site / 'use').mkdir(parents=True)
    (site / 'home.html').write_text(page('Accueil'), encoding='utf-8')
    (site / 'terms-of-use.html').write_text(page('Conditions'), encoding='utf-8')
    (site / 'use' / 'OVERVIEW.html').write_text(page('Introduction à Utilisation'), encoding='utf-8')
    (site / 'use' / 'collecting-data.html').write_text(NAV_PAGE, encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    return site


def book(base_path):
    return {'title': 'DHIS2 User Guide', 'link': 'use/collecting-data.html', 'base_path': base_path,
            'cover': 'cover.jpg', 'category': 'use'}


def titles(nav):
    return [link['title'] for link in nav]


def test_non_book_pages_are_removed_whatever_their_title(localised_site):
    reader = navReader(remote=False, base=BASE)
    doc = book('')
    reader.get_nav([doc])
    assert titles(doc['nav']) == ['Utilisation']
    assert titles(doc['nav'][0]['children']) == ['Collecte des données']


def test_site_section_intro_is_found_whatever_its_title(localised_site):
    reader = navReader(remote=False, base=BASE)
    doc = book('use/')
    reader.get_nav([doc])
    reader.concatenate_docs()
    assert doc['intro'] == '<p>Introduction &agrave; Utilisation</p>'
    with open(os.path.join(localised_site, 'dhis2-user-guide.html'), encoding='utf-8') as f:
        assert '<p>Introduction &agrave; Utilisation</p>' in f.read()


@pytest.mark.parametrize('link, is_section', [
    ({'title': 'Gérer', 'children': [{'title': 'Gérer', 'link': 'target/en/manage/manage.html'}]}, True),
    ({'title': 'Utilisation', 'link': 'target/en/use/overview.html',
      'children': [{'title': 'Guides', 'children': [{'title': 'Saisie', 'link': 'target/en/use/user-guides/data-entry.html'}]}]}, True),
    ({'title': 'Santé', 'children': [{'title': 'Profil', 'link': 'target/en/implement/health/profile/overview.html'},
                                     {'title': 'VIH', 'link': 'target/en/implement/health/hiv/overview.html'}]}, False),
    ({'title': 'Accueil', 'link': 'target/en/home.html'}, False),
    ({'title': 'Vide', 'children': []}, False),
])
def test_is_site_section(link, is_section):
    assert navReader(remote=False, base=BASE).is_site_section(link) == is_section


def test_is_site_section_with_absolute_base():
    reader = navReader(remote=False, base='/home/runner/work/docs/target/fr/')
    link = {'title': 'Gérer', 'children': [{'title': 'Gérer', 'link': '/home/runner/work/docs/target/fr/manage/manage.html'}]}
    assert reader.is_site_section(link)


def test_builder_defaults_to_english():
    assert book_builder.book_locale.locale == 'en'
