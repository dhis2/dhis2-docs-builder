#!/usr/bin/env python3
"""
Generate llms.txt and llms-v{N}.txt files for AI agent discoverability.

Run from the repo root after building the site:
    python3 generate_llms_txt.py [--target target/en] [--site-base https://docs.dhis2.org/en]

Options can also be set via environment variables:
    DOCS_TARGET      Path to the built site directory
    DOCS_SITE_BASE   Public base URL of the deployed site (no trailing slash)

Outputs
-------
  target/en/llms.txt          Canonical index: non-versioned content + latest stable
                              version per section + link to master (development) pages.
  target/en/llms-master.txt   Development/unreleased API and user-guide pages only.
  target/en/llms-v{N}.txt     One file per older versioned release (legacy).

Versioning logic
----------------
  - Pages with no version tag are always in llms.txt.
  - For each (section, subsection) that has numbered versions, the *highest*
    available number is treated as "latest stable" and included in llms.txt.
  - Pages tagged `master` go in llms-master.txt and are referenced from llms.txt.
  - Everything else (older numbered versions) goes in llms-v{N}.txt files.

Spec compliance (https://llmstxt.org/)
--------------------------------------
  - Single H1 with project name.
  - Blockquote with short project summary (no nested lists).
  - H2 sections with bulleted `- [name](url): optional notes` lists.
  - Trailing `## Optional` section for links that may be skipped.
  - Each link's primary URL points to raw Markdown, so agents fetch
    parse-ready content rather than HTML. The rendered HTML URL is
    offered as a note on each entry.

Deployment note
---------------
  Per the spec, crawlers look for llms.txt at the *site root*
  (https://<host>/llms.txt). This script writes to target/en/llms.txt;
  your deploy step must also publish a copy to the bucket root so
  https://docs.dhis2.org/llms.txt returns 200. For example:
      aws s3 cp target/en/llms.txt s3://<bucket>/llms.txt \\
          --cache-control "public, max-age=3600" \\
          --content-type "text/plain; charset=utf-8"
"""

import argparse
import re
import glob
import os
from collections import defaultdict

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_SITE_BASE = "https://docs.dhis2.org/en"
DEFAULT_TARGET = "target/en"

SECTION_ORDER = ["use", "implement", "manage", "develop", "topics"]

SECTION_LABELS = {
    "use":       "Use",
    "implement": "Implement",
    "manage":    "Manage",
    "develop":   "Develop",
    "topics":    "Topics",
}

SECTION_DESCRIPTIONS = {
    "use": (
        "End-user documentation: user guides for all DHIS2 apps, "
        "Android Capture App, and optional apps."
    ),
    "implement": (
        "Implementation guides: planning and configuration, database design, "
        "Tracker, Android rollout, health domain packages, release information."
    ),
    "manage": (
        "System administration: hosting, server configuration, "
        "concepts, how-to guides, and reference material."
    ),
    "develop": (
        "Developer documentation: Web API reference, OpenAPI specification, "
        "Android SDK, and app development."
    ),
    "topics": (
        "Cross-cutting content: training materials, tutorials, user stories, "
        "and complete printable manuals."
    ),
}

VERSION_RE = re.compile(r"dhis-core-version-(\d+|master(?:configuring)?)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def blob_to_raw(url: str) -> str:
    """Convert a GitHub blob URL to a raw.githubusercontent.com URL."""
    return re.sub(
        r"https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.*)",
        r"https://raw.githubusercontent.com/\1/\2/\3/\4",
        url,
    )


def version_int(v: str) -> int:
    """Numeric sort key; 'master' sorts highest."""
    try:
        return int(v)
    except (ValueError, TypeError):
        return 10_000


def major_version(v: str) -> int:
    """Convert an internal version string to a human-friendly major number (242 → 42)."""
    n = int(v)
    return n - 200 if len(v) == 3 and v.startswith("2") else n


def extract_version(path: str):
    """Return the version string embedded in a path, or None."""
    m = VERSION_RE.search(path)
    if not m:
        return None
    raw = m.group(1)
    return "master" if raw.startswith("master") else raw


def extract_breadcrumb(content: str, fallback: str) -> str:
    """Return the human-readable subsection label from a rendered page."""
    # MkDocs Material emits: class=breadcrumb breadcrumb-path (no quotes, minified)
    m = re.search(r"class=(?:\"[^\"]*)?breadcrumb[^>]*>(.*?)</div>", content, re.DOTALL)
    if m:
        text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        # Strip theme-internal prefixes like "alt__"
        text = re.sub(r"^alt__", "", text).strip()
        if text:
            return text
    return fallback.replace("-", " ").title()


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_pages(target_dir: str, site_base: str) -> list:
    pages = []
    for html_path in sorted(glob.glob(f"{target_dir}/**/*.html", recursive=True)):
        with open(html_path, "r", errors="ignore") as fh:
            content = fh.read()

        edit_m = re.search(
            r'<a href=(https://github[^\s>]+) title="Edit this page"', content
        )
        if not edit_m:
            continue

        blob_url = edit_m.group(1)
        raw_url = blob_to_raw(blob_url)

        title_m = re.search(r"<title>([^<]+)</title>", content)
        title = (
            title_m.group(1).replace(" - DHIS2 Documentation", "").strip()
            if title_m
            else ""
        )

        rel = html_path.replace(f"{target_dir}/", "")
        html_url = f"{site_base}/{rel}"

        parts = rel.split("/")
        top_section = parts[0]
        sub_path = parts[1] if len(parts) > 2 else ""

        version = extract_version(rel)
        breadcrumb = extract_breadcrumb(content, sub_path or top_section)

        pages.append(
            {
                "title": title,
                "html_url": html_url,
                "raw_url": raw_url,
                "rel": rel,
                "top_section": top_section,
                "sub_path": sub_path,
                "breadcrumb": breadcrumb,
                "version": version,
            }
        )
    return pages


# ---------------------------------------------------------------------------
# Versioning strategy
# ---------------------------------------------------------------------------

def classify_pages(pages: list):
    """
    Returns
    -------
    main_pages    Non-versioned + latest-stable-per-subsection pages.
    master_pages  Pages tagged 'master'.
    legacy        Dict mapping version string -> list of pages.
    latest_stable The highest globally observed numbered version string.
    """
    # Find the highest numbered version for each (section, sub_path) tuple
    # so sections with fewer releases aren't penalised.
    subsection_max: dict[tuple, int] = {}
    for p in pages:
        if p["version"] and p["version"] != "master":
            key = (p["top_section"], p["sub_path"])
            subsection_max[key] = max(
                subsection_max.get(key, 0), version_int(p["version"])
            )

    # Global latest stable (for reporting / file headers)
    all_numbered = [v for p in pages if p["version"] and p["version"] != "master"
                    for v in [p["version"]]]
    latest_stable = str(max((version_int(v) for v in all_numbered), default=0))

    main_pages = []
    master_pages = []
    legacy: dict[str, list] = defaultdict(list)

    for p in pages:
        v = p["version"]
        if v is None:
            main_pages.append(p)
        elif v == "master":
            master_pages.append(p)
        else:
            key = (p["top_section"], p["sub_path"])
            if version_int(v) == subsection_max.get(key, -1):
                main_pages.append(p)
            else:
                legacy[v].append(p)

    return main_pages, master_pages, legacy, latest_stable


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def entry(page: dict) -> str:
    """
    Emit a spec-compliant link entry.

    Primary URL is the .md file served alongside the HTML on the docs site.
    The rendered HTML URL is offered as a note after the colon.
    """
    md_url = page['html_url'].replace('.html', '.md')
    return f"- [{page['title']}]({md_url}): {page['html_url']}"


def _annotate_versions(pages: list) -> list:
    """Add version label to breadcrumb for latest-stable pages."""
    def version_label(page):
        v = page["version"]
        if v is None:
            return ""
        return f"(v{major_version(v)} — stable)"
    return [
        {**p, "breadcrumb": f"{p['breadcrumb']} {version_label(p)}".strip()}
        for p in pages
    ]


def render_sections(pages: list, version_suffix: str = "") -> list[str]:
    """Render a list of pages grouped by top section → breadcrumb subsection."""
    lines = []
    by_section: dict[str, list] = defaultdict(list)
    for p in pages:
        by_section[p["top_section"]].append(p)

    for sec in SECTION_ORDER:
        sec_pages = by_section.get(sec, [])
        if not sec_pages:
            continue

        label = SECTION_LABELS.get(sec, sec.title())
        lines.append(f"## {label}")
        lines.append("")

        desc = SECTION_DESCRIPTIONS.get(sec)
        if desc:
            lines.append(f"*{desc}*")
            lines.append("")

        # Group by subsection breadcrumb
        by_sub: dict[str, list] = defaultdict(list)
        for p in sec_pages:
            sub_label = p["breadcrumb"]
            if version_suffix:
                sub_label = f"{sub_label} {version_suffix}"
            by_sub[sub_label].append(p)

        # If only one subsection and it matches the section label, omit heading
        use_sub_headings = len(by_sub) > 1 or list(by_sub.keys())[0].lower() != label.lower()

        for sub_label, sub_pages in by_sub.items():
            if use_sub_headings:
                lines.append(f"### {sub_label}")
                lines.append("")
            for p in sub_pages:
                lines.append(entry(p))
            lines.append("")

    return lines


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def write_main(
    main_pages: list,
    master_pages: list,
    legacy: dict,
    latest_stable: str,
    output_path: str,
    site_base: str = DEFAULT_SITE_BASE,
):
    """Write the compact top-level index that links to per-section files."""
    older = sorted(legacy.keys(), key=version_int, reverse=True)

    lines = [
        "# DHIS2 Documentation",
        "",
        "> DHIS2 (District Health Information Software 2) is an open-source platform",
        "> for health information management, used in 100+ countries. This site covers",
        "> end-user guides, implementation, system administration, and developer APIs.",
        "",
        f"**Latest stable release**: v{major_version(latest_stable)}. "
        "Development source: `master` branch.",
        "",
        "Each section below links to a dedicated file listing all pages in that",
        "category. Each page entry gives the raw Markdown source URL (primary) and",
        "the rendered HTML URL (after the colon).",
        "",
        "---",
        "",
        "## Documentation",
        "",
    ]

    for sec in SECTION_ORDER:
        sec_pages = [p for p in main_pages if p["top_section"] == sec]
        if not sec_pages:
            continue
        label = SECTION_LABELS.get(sec, sec.title())
        desc = SECTION_DESCRIPTIONS.get(sec, "")
        lines.append(
            f"- [{label}](llms-{sec}.txt): {desc} ({len(sec_pages)} pages)"
        )

    lines += [
        "",
        "---",
        "",
        "## Optional",
        "",
        "*Supplementary resources. Per the llms.txt spec, agents may skip this",
        "section if a shorter context is needed.*",
        "",
    ]

    if master_pages:
        lines.append(
            "- [Development versions index (master branch)](llms-master.txt): "
            f"{len(master_pages)} unreleased or in-progress pages, "
            "tracks the `master` branch of each source repo"
        )

    lines += [
        f"- [Sitemap]({site_base}/sitemap.xml): full list of all pages (XML)",
        f"- [Search index]({site_base}/search/search_index.json): "
        "full-text search index for all pages (large JSON file)",
    ]

    for v in older:
        major = major_version(v)
        lines.append(
            f"- [DHIS2 v{major} docs (legacy)](llms-v{major}.txt): "
            "older release, not recommended for new work"
        )

    lines.append("")
    _write(output_path, lines)
    print(
        f"  llms.txt          {len(main_pages):4d} total pages "
        f"(compact index → {len(SECTION_ORDER)} section files)"
    )


def write_master(master_pages: list, output_path: str):
    lines = [
        "# DHIS2 Documentation — master (development)",
        "",
        "> These pages are built from the `master`/`main` branch of each source",
        "> repository and reflect features that are in active development or not",
        "> yet released. For the latest stable release see [llms.txt](llms.txt).",
        "",
        "---",
        "",
    ]
    lines += render_sections(master_pages, version_suffix="(master — development)")
    _write(output_path, lines)
    print(f"  llms-master.txt   {len(master_pages):4d} pages")


def write_section(
    main_pages: list,
    section: str,
    output_path: str,
):
    """Write a per-section llms file (llms-use.txt, llms-develop.txt, etc.)."""
    section_pages = [p for p in main_pages if p["top_section"] == section]
    if not section_pages:
        return

    label = SECTION_LABELS.get(section, section.title())
    desc = SECTION_DESCRIPTIONS.get(section, "")

    lines = [
        f"# DHIS2 Documentation — {label}",
        "",
        f"> {desc}",
        "",
        "> Return to the [main index](llms.txt).",
        "",
        "---",
        "",
    ]
    lines += render_sections(_annotate_versions(section_pages))
    _write(output_path, lines)
    print(f"  llms-{section}.txt{'':<12}{len(section_pages):4d} pages")


def write_legacy(pages: list, version: str, output_path: str):
    major = int(version) - 200 if len(version) == 3 and version.startswith("2") else int(version)
    lines = [
        f"# DHIS2 Documentation — v{major} (legacy)",
        "",
        f"> This file indexes documentation for DHIS2 version {major}.",
        f"> It is provided for reference only. For current documentation see [llms.txt](llms.txt).",
        "",
        "---",
        "",
    ]
    lines += render_sections(pages, version_suffix=f"(v{major})")
    _write(output_path, lines)
    print(f"  llms-v{major}.txt       {len(pages):4d} pages")


def _write(path: str, lines: list[str]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--target",
        default=os.environ.get("DOCS_TARGET", DEFAULT_TARGET),
        help="Path to the built site directory "
             "[env: DOCS_TARGET, default: %(default)s]",
    )
    parser.add_argument(
        "--site-base",
        default=os.environ.get("DOCS_SITE_BASE", DEFAULT_SITE_BASE),
        help="Public base URL of the deployed site (no trailing slash) "
             "[env: DOCS_SITE_BASE, default: %(default)s]",
    )
    args = parser.parse_args()

    target = args.target.rstrip("/")
    site_base = args.site_base.rstrip("/")
    print(f"Scanning {target}/ …")
    print(f"  Site base: {site_base}")

    pages = parse_pages(target, site_base)
    print(f"  Found {len(pages)} pages with edit links")

    main_pages, master_pages, legacy, latest_stable = classify_pages(pages)
    print(f"  Latest stable version: v{major_version(latest_stable)}")
    print(f"  Older versions: {sorted(legacy.keys(), key=version_int)}")
    print("Writing output files:")

    write_main(main_pages, master_pages, legacy, latest_stable,
               output_path=f"{target}/llms.txt", site_base=site_base)
    write_master(master_pages,
                 output_path=f"{target}/llms-master.txt")
    for sec in SECTION_ORDER:
        write_section(main_pages, sec,
                      output_path=f"{target}/llms-{sec}.txt")
    for version, vpages in sorted(legacy.items(), key=lambda kv: version_int(kv[0])):
        write_legacy(vpages, version,
                     output_path=f"{target}/llms-v{major_version(version)}.txt")

    print("Done.")
    print()
    print("Reminder: also publish a copy of llms.txt to the site root")
    print("          (https://docs.dhis2.org/llms.txt) — the spec expects it there.")


if __name__ == "__main__":
    main()
