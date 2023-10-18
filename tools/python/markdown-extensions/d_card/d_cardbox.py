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


class D_cardBoxExtension(Extension):
    """ D_card extension for Python-Markdown. """

    def extendMarkdown(self, md):
        """ Add D_card to Markdown instance. """
        md.registerExtension(self)

        md.parser.blockprocessors.register(D_cardBoxProcessor(md.parser), 'd_cardbox', 180)



class D_cardBoxProcessor(BlockProcessor):
        RE_FENCE_START = r'^!!!!!$' # start line, e.g., `   !!!! `
        RE_FENCE_END = r'^!!!!$'  # last non-blank line, e.g, '!!!\n  \n\n'

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
                    e = etree.SubElement(parent, 'd_card-container')
                    # e.set('class', 'display: inline-block; border: 1px solid red;')
                    self.parser.parseBlocks(e, blocks[0:block_num + 1])
                    # remove used blocks
                    for i in range(0, block_num + 1):
                        blocks.pop(0)
                    return True  # or could have had no return statement
            # No closing marker!  Restore and do nothing
            blocks[0] = original_block
            return False  # equivalent to our test() routine returning False


def makeExtension(**kwargs):  # pragma: no cover
    return D_cardBoxExtension(**kwargs)






