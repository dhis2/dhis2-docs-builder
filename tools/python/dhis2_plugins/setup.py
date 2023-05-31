#!/usr/bin/env python
# coding: utf-8

import setuptools

setuptools.setup(
    name="dhis2_plugins",
    version='0.1.0',
    packages=[],
    entry_points={
        'mkdocs.plugins': [
            'edit_url = edit_url.plugin:EditUrlPlugin',
            'dhis2_docs = dhis2_docs.plugin:Dhis2DocsPlugin',
            'mkdocs_video = mkdocs_video.plugin:MkdocsVideoPlugin',
        ]
    }
)
