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
        config['nav'] = fetcher.crawl_nav_list(config['nav'],'')
        print("Done.")


        # update the Yaml file
        ey = open("mkdocs_gen.yml",'w+')
        ey.write(dhis2_utils.yaml.dump(config, sort_keys=False, default_flow_style=False, Dumper=dhis2_utils.yaml.Dumper))
        ey.close()

        return config

