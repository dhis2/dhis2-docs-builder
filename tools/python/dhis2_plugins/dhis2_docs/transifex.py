#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (c) 2021, University of Oslo
All rights reserved.


@author: philld
"""

import requests
import json
import argparse
import os
import glob
import sys
import tempfile
import frontmatter
from translayer import tx3

class tx:

    def __init__(self,project_slug):

        # Transifex
        # project_slug='meta-who-packages'
        self.tx_token = os.getenv('DHIS2_DOCS_TX_TOKEN')
        self.project_slug=project_slug
        if self.tx_token:
            self.tx = tx3.tx('hisp-uio',self.tx_token,log_level=30)

        self.tx_mode='default'

        self.tx_edit_root='https://www.transifex.com/hisp-uio/'

        # We need to map language codes that DHIS2 doesn't support natively
        # fa_AF --> prs
        # uz@Cyrl --> uz
        # uz@Latn --> uz_UZ
        self.langmap={'fa_AF': 'prs', 'uz@Cyrl':'uz','uz@Latn':'uz_UZ'}



    def push(self,path_to_file,resource_slug,categories,tx_i18n_type):

        print("Pushing",path_to_file,"to transifex...")

        cats = resource_slug.split('__')
        if len(cats) > 1:
            ca = []
            ca.append(cats[0])
            c = ca + categories
        else:
            c = categories
        
        while '' in c:
            c.remove('')

        if not self.tx.project(self.project_slug).resource(resource_slug):
           print("Resource does not exist. Creating.")
           self.tx.project(self.project_slug).new_resource(resource_slug,resource_slug,tx_i18n_type,path=path_to_file,categories=c)
        else:
           self.tx.project(self.project_slug).resource(resource_slug).push(path_to_file)


    def pull(self,path_to_file,resource_slug,language_code):

        print("Pulling",path_to_file,"from transifex...")

        # We need to map language codes that DHIS2 doesn't support natively
        # uz@Cyrl --> uz
        # uz@Latn --> uz_UZ
        # mapped_language_code = language_code.replace("@Latn","_UZ").replace("@Cyrl","")
        mapped_language_code = language_code
        if language_code in self.langmap.keys():
            mapped_language_code = self.langmap[language_code]


        self.tx.project(self.project_slug).resource(resource_slug).pull(language_code,path_to_file)

        # set the appropriate edit url to transifex resource
        translate_path = self.tx_edit_root+self.project_slug+'/translate/#'+language_code+'/'+resource_slug
        fm = frontmatter.load(path_to_file)
        fm['edit_url'] = translate_path
        with open(path_to_file, 'w') as emd:
            print(frontmatter.dumps(fm), file=emd)

    def get_stats(self,resource_slug,language_code):
        return self.tx.project(self.project_slug).resource(resource_slug).language_stats(language_code)


