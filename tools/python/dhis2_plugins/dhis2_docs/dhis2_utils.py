#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2020 philld <philld@remspace>
#
# Distributed under terms of the MIT license.

"""

"""
import json
import yaml
import re
import unicodedata
import uuid
import shutil
import os
import sys
import argparse
import hashlib
from git.repo.base import Repo
import MarkdownPP


class helpers:
    def slugify(self, value, allow_unicode=False):
        """
        Convert to ASCII if 'allow_unicode' is False. Convert spaces to hyphens.
        Remove characters that aren't alphanumerics, underscores, or hyphens.
        Convert to lowercase. Also strip leading and trailing whitespace.
        """
        value = str(value)
        if allow_unicode:
            value = unicodedata.normalize('NFKC', value)
        else:
            value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
        value = re.sub(r'[^\w\s-]', '', value).strip().lower()
        return re.sub(r'[-\s]+', '-', value)

class fetcher:

    # Initializing
    def __init__(self):
        # set up a temporary directory for github clones
        # id = uuid.uuid4().hex
        self.root = "tmp/github" #/" + id
        os.makedirs(self.root, exist_ok=True)

        self.docs_dir = 'docs/'
        self.alternate_prefix = 'alt__'
        self.github_base = 'https://github.com/'

    # Calling destructor
    def __del__(self):
        # Delete all temporary files
        #shutil.rmtree(self.root)
        print("goodbye")


    def include_git(self, github_repo, file_path, branch, local_path):

        tmpRoot = self.root + '/' + github_repo + '/' + branch
        git_url = self.github_base + github_repo + ".git"
        destination = self.docs_dir + local_path

        if not os.path.isdir(tmpRoot):
            os.makedirs(os.path.dirname(tmpRoot), exist_ok=True)
            branch_opt = '--branch ' + branch
            Repo.clone_from(git_url, tmpRoot, multi_options=[branch_opt,'--depth 1'])

        if not os.path.isfile(destination):
            os.makedirs(os.path.dirname(destination), exist_ok=True)

        print("Copying file: " + tmpRoot + "/" + file_path + " to " + destination)
            ## markdown pre-process instead of direct copy
        self.markdown_preprocess(tmpRoot + "/" + file_path, destination)


    def markdown_preprocess(self,fromfile, tofile):


        mdpp = open(fromfile, 'r')
        md = open(tofile, 'w')

        modules = list(MarkdownPP.modules)

        MarkdownPP.MarkdownPP(input=mdpp, output=md, modules=modules, fromdir=os.path.dirname(fromfile))

        mdpp.close()
        md.close()

        # copy the images
        f = open(tofile, "r")
        markdown = f.read()
        #print(markdown)
        self.copy_markdown_images(os.path.dirname(fromfile), markdown, tofile)
        f.close()


    def copy_markdown_images(self, basedir, markdown, dest):
        # root = os.path.dirname(os.path.dirname(self.page.url))
        # root = page.url

        # paths = []

        p = re.compile(".*\]\((.*\.[pPnNgGjJeE]{3,4})\)")
        it = p.finditer(markdown)
        for match in it:
            path = match.group(1)

            destinationPath = os.path.realpath(os.path.dirname(dest)+'/'+path)

            if not os.path.isfile(destinationPath):
                try:
                    # print("Copying image: " + basedir + "/" + path + " to " + destinationPath)
                    os.makedirs(os.path.dirname(destinationPath), exist_ok=True)
                    shutil.copyfile(basedir + "/" + path, destinationPath)
                except FileNotFoundError:
                    print("Referenced image not found:",basedir + "/" + path)
                    pass


    def fetch_file(self, file_def, path):
        new_nav = path+'.md'
        # print(new_nav,file_def.split('(')[0])
        if file_def.split('(')[0] == "@github":
            parts = file_def.split('(')[1].strip(' )').split(',')
            github_repo = parts[0].strip()
            git_file = parts[1].strip()
            git_branch = parts[2].strip()
            try:
                decompose = parts[3].strip()
            except:
                decompose = 0
                pass

            # print(github_repo,git_file,git_branch)
            if git_file.endswith('.md'):
                self.include_git(github_repo, git_file, git_branch, new_nav)
                if decompose:
                    new_nav = self.chapterise(new_nav)
            else:
                print("Git file format not supported (must be .md):",git_file)


        return new_nav


    def crawl_nav_list(self, nav, path):
        x = []
        for nav_item in nav:
            if type(nav_item) == dict:
                #print(nav_item)
                nav_item = self.crawl_nav_dict(nav_item,path)
            else:
                if type(nav_item) == list:
                    nav_item = self.crawl_nav_list(nav_item,path)
                else:
                    if nav_item[0] == '(':
                        nav_item = self.fetch_file(nav_item,path)
            x.append(nav_item)
        return x


    def crawl_nav_dict(self, nav, path):
        x={}
        delim = '/'
        if path == '':
            delim = ''
        for k, n in nav.items():
            p = path + delim + helpers().slugify(k.replace(self.alternate_prefix,''))
            if type(n) == dict:
                n = self.crawl_nav_dict(nav[k],p)
            else:
                if type(n) == list:
                    n = self.crawl_nav_list(nav[k],p)
                else:
                    if n[0] == '@':
                        n = self.fetch_file(nav[k],p)
            x[k] = n

        return x


    def chapterise(self, book, editpath=None):

        bmap={}
        content = []
        with open(self.docs_dir + book) as ob:
            lines = ob.readlines()
            chapter=0
            no_title=True
            lastchapter=""
            lastname=None
            lastfound=""
            codebloc=False
            for line in lines:
                try:
                    if not codebloc:
                        # check if the line matches "# <Title>"
                        # if so, treat as a new chapter
                        found = re.search('^#{1,2}? (.+?)($|<!--.*$)', line.rstrip()).group(1)
                        newname = helpers().slugify(found)
                        edit = ""
                        if newname:
                            if editpath:
                                edit = editpath
                            else:
                                try:
                                    edit = re.search('<!-- DHIS2-EDIT:(.*)-->', line.rstrip()).group(1)
                                except AttributeError:
                                    edit = ""


                        if lastname:
                            chk = hashlib.md5(lastchapter.encode('utf-8')).hexdigest()
                            lc = open(self.docs_dir + lastname,'w')
                            lc.write(lastchapter)
                            lc.close
                            try:
                                bmap[newname] += [chk]
                                if newname == "tanzania-integrated-health-information-architecture":
                                    newname += "_B"
                            except KeyError:
                                bmap.update({newname:[chk]})

                        lastname = os.path.dirname(book)+'/'+newname + '.md'
                        lastfound = found

                        if edit:
                            lastchapter = '---\nedit_url: '+edit+'\n---\n# '+found+'\n'
                        else:
                            lastchapter = line
                        content.append({lastfound: lastname})

                        chapter+=1
                        # start a new chapter
                except AttributeError:
                    # error message does not match the pattern
                    found = '' # apply error handling

                try:
                    if line[:2] == "``":
                        #print(line)
                        if codebloc:
                            codebloc = False
                        else:
                            codebloc = True
                except:
                    pass

                # if chapter == 0 and no_title:
                #     try:
                #         title = re.search('^title:[ \'\"]*(.+?)[ \'\"]*$', line.rstrip()).group(1)
                #         # content += '        '+title+':\n'
                #         no_title = False
                #     except AttributeError:
                #         pass

                if found == '':
                    # continue current chapter
                    lastchapter += line


            if lastname:
                chk = hashlib.md5(lastchapter.encode('utf-8')).hexdigest()
                lc = open(self.docs_dir + lastname,'w')
                lc.write(lastchapter)
                lc.close

                try:
                    bmap[newname] += [chk]
                except KeyError:
                    bmap.update({newname:[chk]})

        # return the array of pages
        return content
