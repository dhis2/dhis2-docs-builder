# Tests that the book templates are well-formed. An unmatched closing tag moves later
# chapters out of the book content, where paged.js loses their direction and styling.
import os
import re

import pytest

from book_locale import I18N_DIR

TEMPLATES_DIR = os.path.join(os.path.dirname(I18N_DIR), 'templates')
TEMPLATES = sorted(name for name in os.listdir(TEMPLATES_DIR) if name.endswith('.html'))


@pytest.mark.parametrize('template', TEMPLATES)
@pytest.mark.parametrize('tag', ['div', 'section', 'article'])
def test_template_tags_are_balanced(template, tag):
    with open(os.path.join(TEMPLATES_DIR, template), encoding='utf-8') as f:
        html = f.read()
    opened = len(re.findall(rf'<{tag}[\s>]', html))
    closed = len(re.findall(rf'</{tag}>', html))
    assert opened == closed
