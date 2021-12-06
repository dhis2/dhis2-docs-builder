from logging import NullHandler, fatal
from mkdocs.plugins import BasePlugin
from mkdocs.config import config_options
import mkdocs.structure.files
from . import dhis2_utils
from weasyprint import HTML
from os.path import relpath
import subprocess



class Dhis2DocsPlugin(BasePlugin):

    config_scheme = (
        ('make_pdfs', config_options.Type(bool, default=False)),
        ('tx_project_slug', mkdocs.config.config_options.Type(str, default='docs-full-site')),
        ('template', mkdocs.config.config_options.Type(str, default='default'))
    )

    def __init__(self):
        self.html = HTML
        self.global_toc = {}
        self.current_page = ""

    def on_page_context(self, context, page, config, **kwargs):
        # page.edit_url = ""
        # if 'edit_url' in page.meta:
        #     page.edit_url = page.meta['edit_url']
        return context

    def on_config(self, config):

        # set the language based on environment
        lang = dhis2_utils.os.getenv('DHIS2_DOCS_LANGUAGE')
        if lang == None:
            lang = 'en'
        config['site_url'] = config['site_url'].replace('/en','/'+lang)
        config['site_dir'] = config['site_dir'].replace('/en','/'+lang)
        config['theme']['language'] = lang[0:2]
        config['theme']['language_select'] = lang

        fetcher = dhis2_utils.fetcher(config,self.config['tx_project_slug'],self.config['template'])
        if lang != 'en':
            fetcher.pull_translations(lang,'nav')
        # fetcher.say_hello()
        print("Fetching documents...")
        version_map = {}
        expanded_nav = fetcher.expand_nav_list(config['nav'])
        fetched = fetcher.crawl_nav_list(expanded_nav,'',version_map,[])
        config['nav'] = fetched[0]
        config['version_map'] = fetched[1]
        self.global_toc = fetcher.global_toc

        print("Done.")
        fetcher.configure_translations(config)

        # Push English source files to transifex
        if lang == 'en':
            # run prettier over the markdown to remove line wrapping (ensures consistent
            # formatting for transifex)
            try:
                print("Formatting files with prettier and removing line wrapping...")
                prettify = subprocess.Popen(['prettier', '--prose-wrap', 'never', '--tab-width', '4', '--write', 'docs/**/*.md'])
                prettify.wait()
                print("Done.")

                # Only attempt to push sources to transifex if the files are successfully formatted
                fetcher.push_translations()

            except OSError:
                print("prettier not found. Markdown files may render differently in the official build.")

        # Pull translated versions of files from transifex if necessary
        if lang != 'en':
            fetcher.pull_translations(lang)


        # update the Yaml file
        ey = open("mkdocs_gen.yml",'w+')
        ey.write(dhis2_utils.yaml.dump(config['nav'], sort_keys=False, default_flow_style=False, Dumper=dhis2_utils.yaml.Dumper))
        ey.close()

        return config


    def on_files(self, files, config):
        lister = dhis2_utils.lister()
        nav_pages = lister.crawl_page_list(config['nav'])

        out = []
        for i in files:
            if i.is_documentation_page() and (i.src_path not in nav_pages):
                if i.src_path.split('/')[-1] != 'index.md':
                    continue
            out.append(i)

        return mkdocs.structure.files.Files(out)


    def on_page_markdown(self, markdown, page, config, files):

        # print(page.url)
        self.current_page = page.url

        # remove any remaining DHIS2-EDIT comments from markdown
        md = dhis2_utils.re.sub(r'<!-- DHIS2-EDIT:[^>]*?-->','',markdown)

        # find any links referring to anchor tags, and resolve the path
        q = dhis2_utils.re.compile('(\[[^\]]*])(\(#[^) ]* *\))')
        md2 = q.sub(self.linkfixer,md)

        return md2

    def linkfixer(self, matchobj):
        # We have a link to an anchor. Now we have to find the anchor in the documents
        # Ideally the anchor is unique. If not, we will find the "closest" document containing the anchor

        # By default the link is just the plain anchor, unchanged.
        new_link = matchobj.group(2)

        l = new_link.strip('()')
        # check if the link matches any anchors in the docs
        if l in self.global_toc:
            anchor_count = 0
            closest = None
            ambiguities = []
            for anchor in self.global_toc[l]:
                noskip = True
                # If the anchor is in a different version to the current page, then ignor it
                for x in dhis2_utils.re.findall("[^/]*-version-[^/]*", anchor):
                    if (dhis2_utils.re.sub('[0-9]+','',x) in self.current_page) or (dhis2_utils.re.sub('master','',x) in self.current_page):
                        if x not in self.current_page:
                            noskip = False
                            break

                if noskip:
                    anchor_count += 1
                    ambiguities.append(anchor)
                    rel_link = relpath(anchor, '/'.join(self.current_page.split('/')[:-1]))
                    # print("anchor,current,rel:\n\t",anchor,"\n\t",'/'.join(self.current_page.split('/')[:-1]),"\n\t",rel_link)
                    rel_precode = relpath(anchor.replace('.md','/'), self.current_page.replace('.html','/'))
                    rel_coded = dhis2_utils.re.sub('[^/.]+','C',rel_precode).replace('..','P').replace('.C','/')
                    # print("coded:",rel_coded)
                    if closest:
                        if rel_coded < closest:
                            new_link = '(' + rel_link + l + ')'
                            closest = rel_coded
                    else:
                        new_link = '(' + rel_link + l + ')'
                        closest = rel_coded
                    if rel_coded == '.':
                        # if the anchor is in the same file, then ignore other files (treat as unambiguous)
                        anchor_count = 1
                        break


            if anchor_count > 1:
                print("WARNING -  Link '{}' in file '{}' is ambiguous:".format(l,self.current_page))
                for a in ambiguities:
                    print("           {}{}".format(a,l))

                # print("         The first anchor with that name, in the closest document, will be used")

        ret = matchobj.group(1)+new_link
        return ret


    def on_post_build(self, config):
        if not "search" in config["plugins"]:
            logger.debug(
                "dhis2-search-mod plugin is activated but has no effect as search "
                "plugin is deactivated!"
            )
        else:

            search_index_fp = config.data["site_dir"] + "/search/search_index.json"
            with open(search_index_fp, "r") as f:
                search_index = dhis2_utils.json.load(f)

            temp_records = []
            included_records = []
            matching_paragraphs = []
            unique_records = set()


            for rec in reversed(search_index["docs"]):

                versions = []
                text_cksum = ""
                ignore = False

                loc = rec["location"] #.strip('.md')

                try:
                    loc = dhis2_utils.re.search('(.+?)\.html.*', rec["location"]).group(1)

                    locdir = dhis2_utils.os.path.dirname(loc)

                    if loc in config['version_map']:
                        versions = config['version_map'][loc]
                        text_cksum = dhis2_utils.hashlib.md5((rec['title']+rec['text']).encode('utf-8')).hexdigest()
                    else:
                        if locdir in config['version_map']:
                            versions = config['version_map'][locdir]
                            text_cksum = dhis2_utils.hashlib.md5((rec['title']+rec['text']).encode('utf-8')).hexdigest()

                    for v in versions:
                        rec["title"] += '<v-tag>' + v + '</v-tag>'

                except AttributeError:
                    # .html not found in the location
                    pass

                if text_cksum == "":
                    # included_records.insert(0,rec)
                    unique_records.add(rec['location'])
                else:
                    if text_cksum not in matching_paragraphs:
                        unique_records.add(loc+'.html')
                        unique_records.add(rec['location'])
                        matching_paragraphs.append(text_cksum)

                temp_records.insert(0,rec)

            for rec in temp_records:
                if rec['location'] in unique_records:
                    included_records.append(rec)

            search_index["docs"] = included_records
            with open(search_index_fp, "w") as f:
                dhis2_utils.json.dump(search_index, f)


        if self.config['make_pdfs']:

            for dirpath, dirnames, filenames in dhis2_utils.os.walk(config['site_dir']):
                for filename in [f for f in filenames if f.endswith(".html")]:
                    # don't convert files that are in the root (index files)
                    if (dirpath != config['site_dir']):
                        html_file = dhis2_utils.os.path.join(dirpath, filename)
                        print("Converting to PDF:",html_file)
                        pdf_file = html_file.replace('.html','.pdf')
                        self.html(html_file).write_pdf(pdf_file)
                        print("Converting to PDF: Done.")



        return config
