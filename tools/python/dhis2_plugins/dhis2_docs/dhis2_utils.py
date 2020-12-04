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
import io
import mmap
import sys
import argparse
import hashlib
import fileinput
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

    def grep(self, pattern, file_path):
        with io.open(file_path, "r", encoding="utf-8") as f:
            return re.search(pattern, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ))

class lister:

    def __init__(self):
        self.h = helpers()

    def crawl_page_list(self, nav):
        pages = []
        for nav_item in nav:
            if type(nav_item) == dict:
                #print(nav_item)
                page = self.crawl_page_dict(nav_item)
            else:
                if type(nav_item) == list:
                    page = self.crawl_page_list(nav_item)
            pages = pages + page
        return pages

    def crawl_page_dict(self, nav):
        pages=[]
        for k, n in nav.items():
            if type(n) == dict:
                page = self.crawl_page_dict(nav[k])
            else:
                if type(n) == list:
                    page = self.crawl_page_list(nav[k])
                else:
                    page = [n]
            pages = pages + page

        return pages

class fetcher:

    # Initializing
    def __init__(self):
        # set up a temporary directory for github clones
        # id = uuid.uuid4().hex
        self.h = helpers()
        self.root = "tmp/github" #/" + id
        os.makedirs(self.root, exist_ok=True)

        self.docs_dir = 'docs/'
        self.alternate_prefix = 'alt__'
        self.github_base = 'https://github.com/'

    # Calling destructor
    # def __del__(self):
    #     # Delete all temporary files
    #     shutil.rmtree(self.root)


    def include_git(self, github_repo, file_path, branch, local_path):

        tmpRoot = self.root + '/' + github_repo + '/' + branch
        git_url = self.github_base + github_repo + ".git"

        if not os.path.isdir(tmpRoot):
            os.makedirs(os.path.dirname(tmpRoot), exist_ok=True)
            branch_opt = '--branch ' + branch
            Repo.clone_from(git_url, tmpRoot, multi_options=[branch_opt,'--depth 1'])

        self.include_file(tmpRoot + "/" + file_path, local_path)


    def include_file(self, origin, local_path):

        # ensure the destination directory exists
        destination = self.docs_dir + local_path
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        # print("Copying file: " + origin + " to " + destination)
        if self.h.grep(b'!INCLUDE', origin ):
            # markdown pre-process instead of direct copy
            self.markdown_preprocess(origin, destination)
        else:
            # do a direct copy
            shutil.copyfile(origin, destination)
            # copy the images
            f = open(destination, "r")
            markdown = f.read()
            #print(markdown)
            self.copy_markdown_images(os.path.dirname(origin), markdown, destination)
            f.close()



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

        # fix references to __common__ images
        relative_dir = os.path.relpath('./',os.path.dirname(tofile))
        for line in fileinput.input([tofile], inplace=True):
            print(line.replace('__common__', relative_dir).replace('resources/images/../..',relative_dir), end='')


    def copy_markdown_images(self, basedir, markdown, dest):
        # root = os.path.dirname(os.path.dirname(self.page.url))
        # root = page.url

        # paths = []

        p = re.compile("!\[[^\]]*\]\((.*?)(?:\s+\"(.*[^\"])\"?)?\s*\)")
        it = p.finditer(markdown)
        for match in it:
            path = match.group(1)

            if path[0:10] != '__common__':
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


        if file_def.split('(')[0] == "@file":
            parts = file_def.split('(')[1].strip(' )').split(',')
            local_file = parts[0].strip()
            try:
                decompose = parts[1].strip()
            except:
                decompose = 0
                pass

            # print(github_repo,git_file,git_branch)
            if local_file.endswith('.md'):
                self.include_file(local_file, new_nav)
                if decompose:
                    new_nav = self.chapterise(new_nav)
            else:
                print("File format not supported (must be .md):",local_file)


        return new_nav


    def crawl_nav_list(self, nav, path, v_map, v_tmp):
        x = []
        for nav_item in nav:
            if type(nav_item) == dict:
                #print(nav_item)
                nav_item, v_map = self.crawl_nav_dict(nav_item,path, v_map, v_tmp)
            else:
                if type(nav_item) == list:
                    nav_item, v_map = self.crawl_nav_list(nav_item,path, v_map, v_tmp)
                else:
                    if nav_item[0] == '(':
                        v_map[path] = v_tmp
                        nav_item = self.fetch_file(nav_item,path)
            x.append(nav_item)
        return x, v_map


    def crawl_nav_dict(self, nav, path, v_map, v_tmp):
        x={}
        delim = '/'
        if path == '':
            delim = ''
        for k, n in nav.items():
            no_pref = k.replace(self.alternate_prefix,'')
            p = path + delim + self.h.slugify(no_pref)
            tmp_v = v_tmp
            if no_pref != k:
                # this is an "alternate" - keep track of it
                tmp_v = v_tmp + [no_pref]
                # print("alternate", k , tmp_v)
            if type(n) == dict:
                n, v_map = self.crawl_nav_dict(nav[k],p, v_map, tmp_v)
            else:
                if type(n) == list:
                    n, v_map = self.crawl_nav_list(nav[k],p, v_map, tmp_v)
                else:
                    if n[0] == '@':
                        v_map[p] = tmp_v
                        # print(p,tmp_v)
                        n = self.fetch_file(nav[k],p)
            x[k] = n

        return x, v_map



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
                        found = re.search('^# (.+?)($|<!--.*$)', line.rstrip()).group(1)
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
                            os.makedirs(os.path.dirname(self.docs_dir + lastname), exist_ok=True)
                            lc = open(self.docs_dir + lastname,'w')
                            lc.write(lastchapter)
                            lc.close
                            try:
                                bmap[newname] += [chk]
                                if newname == "tanzania-integrated-health-information-architecture":
                                    newname += "_B"
                            except KeyError:
                                bmap.update({newname:[chk]})

                        lastname = os.path.dirname(book)+'/' + os.path.basename(book).replace('.md','') + '/' + newname + '.md'
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
                    lastchapter += re.sub(r'\]\(\s*([^)]*resources/images/)',r'](../\1',line)  #.replace('(resources/images/','(../resources/images/')


            if lastname:
                chk = hashlib.md5(lastchapter.encode('utf-8')).hexdigest()
                os.makedirs(os.path.dirname(self.docs_dir + lastname), exist_ok=True)
                lc = open(self.docs_dir + lastname,'w')
                lc.write(lastchapter)
                lc.close

                try:
                    bmap[newname] += [chk]
                except KeyError:
                    bmap.update({newname:[chk]})

        # return the array of pages
        return content
