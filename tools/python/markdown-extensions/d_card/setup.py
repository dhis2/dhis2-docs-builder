from setuptools import setup
setup(
    name='d_card',
    version='1.0',
    py_modules=['d_card'],
    install_requires = ['markdown>=2.5'],
    entry_points={
        'markdown.extensions': [
            'd_card = d_card:D_cardExtension',
            'd_cardbox = d_cardbox:D_cardBoxExtension',
        ]
    }
)

