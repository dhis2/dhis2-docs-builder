from mkdocs.plugins import BasePlugin
from . import dhis2_utils

class Dhis2DocsPlugin(BasePlugin):
    def on_page_context(self, context, page, config, **kwargs):
        # page.edit_url = ""
        # if 'edit_url' in page.meta:
        #     page.edit_url = page.meta['edit_url']
        return context

    def on_config(self, config):
        fetcher = dhis2_utils.fetcher()
        # fetcher.say_hello()
        print("Fetching documents...")
        version_map = {}
        fetched = fetcher.crawl_nav_list(config['nav'],'',version_map)
        config['nav'] = fetched[0]
        config['version_map'] = fetched[1]

        print(dhis2_utils.json.dumps(config['version_map']))
        print("Done.")


        # update the Yaml file
        ey = open("mkdocs_gen.yml",'w+')
        ey.write(dhis2_utils.yaml.dump(config, sort_keys=False, default_flow_style=False, Dumper=dhis2_utils.yaml.Dumper))
        ey.close()

        return config
        
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

                    print("LOC: ", loc, locdir)

                    if loc in config['version_map']:
                        versions = config['version_map'][loc]
                    else:
                        if locdir in config['version_map']:
                            versions = config['version_map'][locdir]


                    for v in versions:
                        rec["title"] = rec["title"] + '<div class="v-tag">' + v + '</div>'

                except AttributeError:
                    # .html not found in the location
                    pass 



                included_records.append(rec)

            search_index["docs"] = included_records
            with open(search_index_fp, "w") as f:
                dhis2_utils.json.dump(search_index, f)

        return config

