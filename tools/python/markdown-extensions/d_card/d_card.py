"""
D_card extension for Python-Markdown
========================================

Adds rST-style d_cards. Inspired by [rST][] feature with the same name.

[rST]: http://docutils.sourceforge.net/docs/ref/rst/directives.html#specific-d_cards  # noqa

See <https://Python-Markdown.github.io/extensions/d_card>
for documentation.

Original code Copyright [Tiago Serafim](https://www.tiagoserafim.com/).

All changes Copyright The Python Markdown Project

License: [BSD](https://opensource.org/licenses/bsd-license.php)

"""

from markdown.extensions import Extension
from markdown.blockprocessors import BlockProcessor
# from markdown.util import etree
import xml.etree.ElementTree as etree
import re


class D_cardExtension(Extension):
    """ D_card extension for Python-Markdown. """

    def extendMarkdown(self, md):
        """ Add D_card to Markdown instance. """
        md.registerExtension(self)

        md.parser.blockprocessors.register(D_cardProcessor(md.parser), 'd_card', 104)


class D_cardProcessor(BlockProcessor):

    CLASSNAME = 'd_card'
    CLASSNAME_TITLE = 'd_card-title'
    RE = re.compile(r'(?:^|\n)!!! ?(.*)? *(?:\n|$)')
    RE_SPACES = re.compile('  +')

    def test(self, parent, block):
        sibling = self.lastChild(parent)
        return self.RE.search(block) or \
            (block.startswith(' ' * self.tab_length) and sibling is not None and
             sibling.get('class', '').find(self.CLASSNAME) != -1)

    def run(self, parent, blocks):
        sibling = self.lastChild(parent)
        block = blocks.pop(0)
        m = self.RE.search(block)

        if m:
            block = block[m.end():]  # removes the first line

        block, theRest = self.detab(block)

        if m:
            title = m.group(1)
            div = etree.SubElement(parent, 'div')
            div.set('class', self.CLASSNAME)
            if title:
                p = etree.SubElement(div, 'p')
                p.text = title
                p.set('class', self.CLASSNAME_TITLE)
        else:
            div = sibling

        self.parser.parseChunk(div, block)

        if theRest:
            # This block contained unindented line(s) after the first indented
            # line. Insert these lines as the first block of the master blocks
            # list for future processing.
            blocks.insert(0, theRest)


class D_cardBlockProcessor(BlockProcessor):
        RE_FENCE_START = r'^ *!{3,} *\n' # start line, e.g., `   !!!! `
        RE_FENCE_END = r'\n *!{3,}\s*$'  # last non-blank line, e.g, '!!!\n  \n\n'

        def test(self, parent, block):
            return re.match(self.RE_FENCE_START, block)

        def run(self, parent, blocks):
            original_block = blocks[0]
            blocks[0] = re.sub(self.RE_FENCE_START, '', blocks[0])

            # Find block with ending fence
            for block_num, block in enumerate(blocks):
                if re.search(self.RE_FENCE_END, block):
                    # remove fence
                    blocks[block_num] = re.sub(self.RE_FENCE_END, '', block)
                    # render fenced area inside a new div
                    e = etree.SubElement(parent, 'div')
                    e.set('style', 'display: inline-block; border: 1px solid red;')
                    self.parser.parseBlocks(e, blocks[0:block_num + 1])
                    # remove used blocks
                    for i in range(0, block_num + 1):
                        blocks.pop(0)
                    return True  # or could have had no return statement
            # No closing marker!  Restore and do nothing
            blocks[0] = original_block
            return False  # equivalent to our test() routine returning False


def makeExtension(**kwargs):  # pragma: no cover
    return D_cardExtension(**kwargs)






