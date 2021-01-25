from mkdocs.plugins import BasePlugin
from mkdocs.config import config_options
import mkdocs.structure.files
from . import dhis2_utils
from weasyprint import HTML

class Dhis2DocsPlugin(BasePlugin):

    config_scheme = (
        ('make_pdfs', config_options.Type(bool, default=False)),
        ('tx_project_slug', mkdocs.config.config_options.Type(str, default='docs-full-site'))
    )

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
        #config['extra']['dhis2_language'] = config['extra']['dhis2_language'].replace('/en/','/'+lang+'/')
        config['theme']['language'] = lang[0:2]

        fetcher = dhis2_utils.fetcher(config,self.config['tx_project_slug'])
        if lang != 'en':
            fetcher.pull_translations(lang,'nav')
        # fetcher.say_hello()
        print("Fetching documents...")
        version_map = {}
        fetched = fetcher.crawl_nav_list(config['nav'],'',version_map,[])
        config['nav'] = fetched[0]
        config['version_map'] = fetched[1]

        print("Done.")
        fetcher.configure_translations(config)

        # Push English source files to transifex
        if lang == 'en':
            fetcher.push_translations()

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

        # remove any remaining DHIS2-EDIT comments from markdown
        md = dhis2_utils.re.sub(r'<!-- DHIS2-EDIT:[^>]*?-->','',markdown,dhis2_utils.re.MULTILINE)

        # if len(dhis2_utils.re.findall(r'^#\s+',md,dhis2_utils.re.MULTILINE)) > 1:
        #     mark2 = md.replace('\n#','\n##')
        #     return mark2

        return md


    def on_post_build(self, config):
        if not "search" in config["plugins"]:
            logger.debug(
                "dhis2-search-mod plugin is activated but has no effect as search "
                "plugin is deactivated!"
            )
        else:
            # to_exclude = self.config["exclude"]
            # to_ignore = self.config["ignore"]
            # if to_exclude:
            #     # TODO: Other suffixes ipynb etc., more robust
            #     to_exclude = [f.replace(".md", "") for f in to_exclude]
            #     if to_ignore:
            #         to_ignore = [f.replace(".md", "") for f in to_ignore]
            #         # subchapters require both the subchapter as well as the main record.
            #         also_ignore = []
            #         for ignore_entry in to_ignore:
            #             if not ignore_entry.endswith(".md"):
            #                 ignore_entry_main_name = ignore_entry.split("#")[0]
            #                 also_ignore.append(ignore_entry_main_name)
            #         to_ignore += also_ignore

            search_index_fp = config.data["site_dir"] + "/search/search_index.json"
            with open(search_index_fp, "r") as f:
                search_index = dhis2_utils.json.load(f)

            included_records = []

            for rec in search_index["docs"]:
                # if rec["location"] == "" or rec["location"].startswith("#"):
                #     included_records.append(rec)
                # else:
                #     rec_main_name, rec_subchapter = rec["location"].split("/")[-2:]

                #     if rec_main_name + rec_subchapter in to_ignore:
                #         # print("ignored", rec["location"])
                #         included_records.append(rec)
                #     elif (
                #         rec_main_name not in to_exclude
                #         and rec_main_name + rec_subchapter
                #         not in to_exclude  # Also ignore subchapters of excluded main records
                #     ):
                #         # print("included", rec["location"])
                #         included_records.append(rec)
                #     else:
                #         logger.info(f"exclude-search: {rec['location']}")

                # if '#' not in rec["location"]:
                versions = []

                loc = rec["location"].strip('.md')

                try:
                    loc = dhis2_utils.re.search('(.+?)\.html.*', rec["location"]).group(1)

                    locdir = dhis2_utils.os.path.dirname(loc)

                    if loc in config['version_map']:
                        versions = config['version_map'][loc]
                    else:
                        if locdir in config['version_map']:
                            versions = config['version_map'][locdir]


                    for v in versions:
                        rec["title"] = rec["title"] + '<v-tag>' + v + '</v-tag>'

                except AttributeError:
                    # .html not found in the location
                    pass



                included_records.append(rec)

            search_index["docs"] = included_records
            with open(search_index_fp, "w") as f:
                dhis2_utils.json.dump(search_index, f)


        if self.config['make_pdfs']:
            
            for dirpath, dirnames, filenames in dhis2_utils.os.walk(config['site_dir']):
                for filename in [f for f in filenames if f.endswith(".html")]:
                    # don't convert files that are in the root (index files)
                    if (dirpath != config['site_dir']):
                        # print("TO PDF:",dhis2_utils.os.path.join(dirpath, filename))
                        print("TO PDF-:",dirpath, filename)
                        html_file = dhis2_utils.os.path.join(dirpath, filename)
                        pdf_file = html_file.replace('.html','.pdf')
                        HTML(html_file).write_pdf(pdf_file)



        return config
