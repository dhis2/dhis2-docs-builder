from setuptools import setup
setup(
    name='d_maxwidth',
    version='1.1',
    py_modules=['d_maxwidth'],
    install_requires = ['markdown>=2.5'],
    entry_points={
        'markdown.extensions': [
            'd_maxwidth = d_maxwidth:D_MaxWidth',
        ]
    }
)

