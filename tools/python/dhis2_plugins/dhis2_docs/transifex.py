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

class tx:

    def __init__(self,project_slug):

        # Transifex
        # project_slug='meta-who-packages'
        self.tx_token = os.getenv('DHIS2_DOCS_TX_TOKEN')
        self.project_slug=project_slug
        # tx_i18n_type='KEYVALUEJSON'
        self.tx_mode='default'
        self.tx_langs_api='https://www.transifex.com/api/2/project/{s}/resource/{r}/?details'
        self.tx_stats_api='https://www.transifex.com/api/2/project/{s}/resource/{r}/stats/{l}'
        self.tx_translations_api='https://www.transifex.com/api/2/project/{s}/resource/{r}/translation/{l}/?mode={m}&file'
        self.tx_resources_api='https://www.transifex.com/api/2/project/{s}/resources/'
        self.tx_resource_api='https://www.transifex.com/api/2/project/{s}/resource/{r}'
        self.tx_content_api='https://www.transifex.com/api/2/project/{s}/resource/{r}/content'
        self.tx_translations_update_api='https://www.transifex.com/api/2/project/{s}/resource/{r}/translation/{l}'
        self.tx_edit_root='https://www.transifex.com/hisp-uio/'

        # We need to map language codes that DHIS2 doesn't support natively
        # fa_AF --> prs
        # uz@Cyrl --> uz
        # uz@Latn --> uz_UZ
        self.langmap={'fa_AF': 'prs', 'uz@Cyrl':'uz','uz@Latn':'uz_UZ'}

        self.TX_AUTH=('api',self.tx_token)

        # get a list of resources for the project
        self.tx_resources = []
        urlr = self.tx_resources_api.format(s=project_slug)
        response = requests.get(urlr, auth=self.TX_AUTH)
        if response.status_code == requests.codes['OK']:
            res = (x['slug'] for x in response.json())
            for resource_s in res:
                self.tx_resources.append(resource_s)


    def push(self,path_to_file,resource_slug,categories,tx_i18n_type):

        print("Pushing",path_to_file,"to transifex...")

        cats = resource_slug.split('__')
        if len(cats) > 1:
            ca = []
            ca.append(cats[0])
            c = ca + categories
        else:
            c = categories

        # check if our resource exists
        if resource_slug in self.tx_resources:
            # If it does - update it
            url = self.tx_content_api.format(s=self.project_slug, r=resource_slug)
            files = {'upload_file': open(path_to_file, "rb")}
            r = requests.put(url, files=files, auth=self.TX_AUTH)
            # print(r.status_code,": PUT ",url)
                # print(r.headers,": PUT ",url)
        else:
            # if it doesn't - create it
            print("Resource does not exist. Creating...")
            url = self.tx_resources_api.format(s=self.project_slug)
            data = {
                'name': resource_slug,
                'slug': resource_slug,
                'i18n_type': tx_i18n_type,
                'categories': c
            }
            files = {'upload_file': open(path_to_file, "rb")}
            r = requests.post(url, files=files, data=data, auth=self.TX_AUTH)
            # print(r.status_code,": POST ",url)

        if r.status_code != requests.codes['OK']:
            print(r.text)

        # if c:
        #     url = self.tx_resource_api.format(s=self.project_slug, r=resource_slug)
        #     data = {
        #         'categories': c
        #     }
        #     r = requests.put(url, data=json.dumps(data), auth=self.TX_AUTH, headers={'content-type': 'application/json'})
        #     if r.status_code != requests.codes['OK']:
        #         print(r.text)

    def pull(self,path_to_file,resource_slug,language_code):

        print("Pulling",path_to_file,"from transifex...")

        # We need to map language codes that DHIS2 doesn't support natively
        # uz@Cyrl --> uz
        # uz@Latn --> uz_UZ
        # mapped_language_code = language_code.replace("@Latn","_UZ").replace("@Cyrl","")
        mapped_language_code = language_code
        if language_code in self.langmap.keys():
            mapped_language_code = self.langmap[language_code]


        url = self.tx_translations_api.format(s=self.project_slug, r=resource_slug, l=language_code, m=self.tx_mode)
        response = requests.get(url, auth=self.TX_AUTH)
        if response.status_code == requests.codes['OK']:
            os.makedirs(os.path.dirname(path_to_file), exist_ok=True)
            with open(path_to_file, 'wb') as f:
                for line in response.iter_content():
                    f.write(line)

            # set the appropriate edit url to transifex resource
            fm = frontmatter.load(path_to_file)
            fm['edit_url'] = self.tx_edit_root+self.project_slug+'/translate/#'+language_code+'/'+resource_slug
            with open(path_to_file, 'w') as emd:
                print(frontmatter.dumps(fm), file=emd)
