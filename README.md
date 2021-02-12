# dhis2-docs-builder

This is the build source for the DHIS2 documentation site.

## Building the documentation

### Requirements and setup

Python3 is required (tested with python 3.8)

Setup the environment
```
source setup_venv
```
This will setup the virtual environment, and download the necessary dependencies. Then,
```
source venv/bin/activate
```
to activate the environment

### Build

The build system is based on [mkdocs](https://www.mkdocs.org/). In it's simplest form, to build the full documentation site, in your environment, you simply need to perform:
```
mkdocs build
```

In addition to standard mkdocs processing, this performs the following steps:

1. Pull any referenced repositories into the `./tmp/github/` folder (if they don't already exist there)
2. Copy any referenced files (and linked images) from those repositories into the `./docs/` folder
3. Generates the documentation into the `./target` folder.

### Custom builds

By default the configuration is taken from the `./mkdocs.yml` file, but you can specify a different file with the `--config-file` argument. E.g.
```
mkdocs build --config-file mkdocs_slim.yml
```
builds the documents defined in mkdocs_slim.yml, which is a slimmed-down set of documents for testing the basic functionality of the site.

If you wish to check the results of building your own documents, I would recommend to make a copy of mkdocs_slim.yml and add your own content to the `nav` section (see #managing-content)


## Managing content

The content of the documentation build is defined fully in the `nav` section of the configuration file (`mkdocs.yml` by default).

The structure is something like the following:

```yaml
nav:
  - Home: '@github(dhis2/dhis2-docs, src/commonmark/en/content/home.md, master)'
  - Use:
      Use: '@github(dhis2/dhis2-docs, src/commonmark/en/content/user/index.md, master)'
      User guide:
        alt__DHIS core version 2.35:
          What is DHIS2?: '@github(dhis2/dhis2-docs, src/commonmark/en/content/user/what-is-dhis2.md,2.35)'
          Collecting data:
            - Data Entry: '@github(dhis2/dhis2-docs, src/commonmark/en/content/user/using-the-data-entry-app.md,2.35)'
          Tracking individual level data:
            - Capture: '@github(dhis2/dhis2-docs, src/commonmark/en/content/user/using-the-capture-app.md,2.35)'
            - Event Capture: '@github(dhis2/dhis2-docs, src/commonmark/en/content/user/using-the-event-capture-app.md,2.35)'
            - Tracker Capture: '@github(dhis2/dhis2-docs, src/commonmark/en/content/user/using-the-tracker-capture-app.md,2.35)'
        alt__DHIS core version 2.34:
          - What is DHIS2?: '@github(dhis2/dhis2-docs, src/commonmark/en/content/user/what-is-dhis2.md,2.34)'
          ...
      Optional Apps:
        Action Tracker App:
          alt__App version 1.0:
            - Dashboard and Demo Server:
              - Introduction: '@github(hisptz/unicef-apps-docs,src/commonmark/en/content/action_tracker/at-app-introduction.md, master)'
              - Browsing: '@github(hisptz/unicef-apps-docs,src/commonmark/en/content/action_tracker/at-app-browsing.md, master)'
  - Implement:
      Implement: '@github(dhis2/dhis2-docs, src/commonmark/en/content/implementation/index.md, master)'
      Implementer guide:
        - A quick guide to DHIS2 implementation: '@github(dhis2/dhis2-docs, src/commonmark/en/content/implementation/a-quick-guide-to-dhis2-implementation.md, master)'
        - Conceptual Design Principles: '@github(dhis2/dhis2-docs, src/commonmark/en/content/implementation/conceptual-design-principles.md, master)'
        ...
```

> **Tip**
>
> When modifying the structure it is an advantage to use an editor that can "fold" the yaml code at different levels.

There are a few things that are special about this configuration. They are explained in the following sections.

### File references

mkdocs usually refers to file paths under the `./docs/`. Our implementation starts with an empty `./docs/` folder and populates it from files in remote github repositories or local paths.

1. Remote GitHub repositories:

   To reference a file in a GitHub repository, we use the following syntax:

   ```
   @github(<GitHub-repo>,<path-to-file>,<GitHub-branch>)
   ```

   This syntax is used for all of the files in the core documentation build.

2. Local paths

   To reference a local file, we can use the following syntax:

   ```
   @file(<path-to-file>)
   ```

   This is particularly useful when testing how a markdown file will be rendered in the final documentation. Simply use this syntax to reference the file you are working on, and it will be pulled into the build (with any linked images).

   > **Note**
   >
   > Files are only copied to `./docs/` if they don't already exist so, when making changes to a file, you should remove it from the `./docs/` folder prior to rebuilding. You can of course simply clean the entire folder: `rm -rf ./docs/*`.

### Folder structure

mkdocs uses the path of the files in the `./docs/` folder to determine the folder structure of the generated documentation. We begin with an empty folder, and populate it with the same structure as the `nav` section of the configuration file, but with the following modifications:

- "Home" is a special page and is used for the `home.html` file in the root of the site
- the `alt__` prefix is a special marker for something we call [alternates](#alternates), and is remove from the folder name.
- Folder names are "slugified"; that is, they are converted into html friendly paths, so
  ```
  - Use:
      User guides:
        alt__DHIS core version 2.35:
          Collecting data:
            - Data Entry: '@github(dhis2/dhis2-docs, src/commonmark/en/content/user/using-the-data-entry-app.md,2.35)'
  ```
  becomes: `use/user-guides/dhis-core-version-235/collecting-data/data-entry.html`

### Alternates

Alternates are a mechanism we have introduced to allow independent versioning of documentation throughout the site.

- Alternates are indicated with the prefix `alt__` in the nav structure
- Alternates can be used from the second navigation level onwards.
  - The first level is used for the top (tabs) menu for the site. Alternates at the second level are displayed as dropdown options in the navigation tabs. This is used for the "Topics" section in the core documentation.
- Alternates at levels 3 and below are hidden from the side navigation, but appear as selections at the top of the page (generally used for versions of the current document, or set of documents).
- Alternates cannot be mixed with "normal" folders; if one entry has an "alt__" prefix, all siblings must have the prefix too. It is, however, OK to have no siblings.
- Alternates can be nested. This can be useful if a particular document is applicable to more than one version; such as a specific DHIS2 version AND a specific App version. *Alternates are not limited to versions, but can be used for any categories that you wish to display as "alternatives" for a given document.*

Probably the easiest way to understand Alternates is to compare the `mkdocs.yml` configuration with the [DHIS2 Docs site](docs.dhis2.org).
