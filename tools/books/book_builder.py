import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from jinja2 import Environment, FileSystemLoader
from slugify import slugify as slugify_unicode
import logging
#import pdfkit
#from pytube import YouTube
import time
import asyncio
from playwright.async_api import async_playwright
import http.server
import socketserver
import threading
from functools import partial
import datetime
import shutil

logging.basicConfig(level=logging.DEBUG)
import os
import subprocess
import tempfile
import yaml

# Increase the file descriptor limit
os.system("ulimit -n 4096")

script_dir = os.path.dirname(os.path.abspath(__file__))
env = Environment(loader=FileSystemLoader(script_dir))

def convert_mermaid_to_png(mermaid_string, output_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mmd") as temp_input:
        temp_input.write(mermaid_string.encode())
        temp_input_path = temp_input.name
    
    command = ['mmdc', '-i', temp_input_path, '-o', output_file]
    
    try:
        subprocess.run(command, check=True)
        print(f"Successfully created {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
    finally:
        temp_input.close()

def get_youtube_thumbnail(video_url):
    yt = YouTube(video_url)
    thumbnail_url = yt.thumbnail_url
    return thumbnail_url

def download_thumbnail(thumbnail_url, save_path='thumbnail.jpg'):
    response = requests.get(thumbnail_url)
    if response.status_code == 200:
        with open(save_path, 'wb') as file:
            file.write(response.content)
    else:
        print("Failed to retrieve thumbnail")


baseUrl = os.getenv('DOC_BASE_URL', './target/en/')
relBase = baseUrl.replace('./','')


docs_yml_path = os.path.join(script_dir, 'docs.yml')
with open(docs_yml_path, 'r') as f:
    docs = yaml.safe_load(f)



class navReader:

    def __init__(self, remote=True, base=''):
        self.remote = remote
        self.base = base
        self.docs = []
        # Only keep truly global state as instance attributes

    def get_nav(self, docs):
        for doc in docs:
            # Initialize per-doc state
            doc['state'] = {
                'parentSections': {'-1': ''},
                'currentDocIntro': None,
                'currentDocFirstLevel': None,
                'levelOffset': 0
            }
            doc['pdfdocs'] = []
            doc['flatlist'] = []
            doc['intro'] = None
            docUrl = urljoin(self.base, doc['link'])
            # get the parent directory of the doc
            if doc['base_path']:
                doc['state']['currentDocBase'] = urljoin(self.base, doc['base_path'])
                doc['state']['levelOffset'] = doc['base_path'].count('/')-1
                print(f"base_path: {doc['base_path']}")
            else:
                doc['state']['currentDocBase'] = '/'.join(docUrl.split('/')[:-2])
            print(f"levelOffset: {doc['state']['levelOffset']}")
            if self.remote:
                response = requests.get(docUrl)
                file_content = response.content
            else:
                with open(docUrl, 'r', encoding="utf-8") as f:
                    file_content = f.read()
            soup = BeautifulSoup(file_content, 'html.parser')
            def extract_links(ul, first=False):
                nav = []
                for li in ul.find_all('li', recursive=False):
                    label = li.find('label')
                    a = li.find('a')
                    if a:
                        fullUrl = urljoin(docUrl,a['href'])
                        linky = {'title': a.text.strip(), 'link': urljoin(docUrl,a['href'])}
                    myUl = li.find('ul')
                    if myUl:
                        if myUl.get('data-md-component') != 'toc':
                            children = extract_links(myUl)
                            linky['children'] = children
                            if 'overview' not in linky['link']:
                                del linky['link']
                                if label:
                                    linky['title'] = label.text.strip()
                    nav.append(linky)
                    if 'link' in linky:
                        doc['flatlist'].append(linky['link'])
                return nav
            def prune_nav(nav):
                # recursively remove links that do not contain currentDocBase or have no children
                nav_out = []
                for link in nav:
                    if 'children' in link:
                        for child in link['children']:
                            if 'link' in child:
                                childName = child['link'].split('/')[-1].split('.')[0]
                                if childName == 'OVERVIEW':
                                    link['link'] = child['link']
                                    link['children'].remove(child)
                        link['children'] = prune_nav(link['children'])
                    if 'link' in link:
                        if doc['state']['currentDocBase'] not in link['link']:
                            continue
                        if 'exclude_paths' in doc:
                            if any(urljoin(self.base, exclude_path) in link['link'] for exclude_path in doc['exclude_paths']):
                                continue
                        if 'children' in link and not link['children']:
                            continue

                        # if the 'link' is duplicated in any of the children, remove it
                        if 'children' in link:
                            for child in link['children']:
                                if 'link' in child and child['link'] == link['link']:
                                    del link['link']
                                    break
                    if link:
                        # if link has an empty children list, remove it
                        if 'children' in link and not link['children']:
                            continue
                        nav_out.append(link)

                # remove Home and Terms-of-use from the nav
                nav_out = [link for link in nav_out if link['title'] not in ['Home', 'Terms of use']]
                return nav_out
            ul = soup.find('nav',{'class':'md-nav md-nav--primary','aria-label':'Navigation'}).find('ul',{'class':'md-nav__list'})
            nav0 = extract_links(ul,True)
            with open('nav0.json', 'w') as f:
                f.write(json.dumps(nav0, indent=2))
            nav1 = []
            for l in nav0:
                if l in ['Use', 'Implement', 'Develop', 'Manage']:
                    nav1.append(l['children'])
                else:
                    nav1.append(l)
            nav = prune_nav(nav1)
            doc['nav'] = nav
            with open('nav1.json', 'w') as f:
                f.write(json.dumps(nav, indent=2))
        self.docs = docs
        with open('docs.json', 'w') as f:
            f.write(json.dumps(docs, indent=2))

    def concatenate_docs(self):
        def fetch_content(link):
            if self.remote:
                response = requests.get(link)
                file_content = response.content
            else:
                with open(link, 'r', encoding="utf-8") as f:
                    file_content = f.read()
            soup = BeautifulSoup(file_content, 'html.parser')
            article = soup.find('article')
            if article.find('div',{'class':'md-content-alternates'}):
                article.find('div',{'class':'md-content-alternates'}).decompose()
            article = article.find_next('div')
            for img in article.find_all('img'):
                realPath = urljoin(link, img['src'])
                frombase = realPath.replace(relBase,'')
                img['src'] = frombase
                # if the image element has an inline width of 25%, set the width to 50%
                if img.get('style') and 'width:25%' in img['style']:
                    img['style'] = img['style'].replace('width:25%', 'width:50%')
            for a in article.find_all('a'):
                # remove if the class is 'headerlink'
                if a.get('class') and 'headerlink' in a['class']:
                    a.decompose()
                    continue
                if 'html#' in a['href']:
                    inList = False
                    for link in doc['flatlist']:
                        if a['href'].split('#')[0] in link:
                            a['href'] = '#'+a['href'].split('#')[1]
                            inList = True
                            break
            articleString = str(article.decode_contents(eventual_encoding="utf-8", formatter='html'))
            return articleString
        def append_nav(nav, state, level=0):
            full = ''
            for link in nav:
                if link['title'] in ['Use', 'Implement', 'Develop', 'Manage'] and level == 0:
                    if 'link' in link and not state['currentDocIntro']:
                        state['currentDocIntro'] = fetch_content(link['link'])
                        doc['intro'] = state['currentDocIntro']
                    if 'children' in link:
                        full += append_nav(link['children'], state, level+1)
                else:
                    print("here")
                    full += f'\n'
                    # create a unique id from title and timestamp
                    unique_id = slugify_unicode(link['title']) + str(int(time.time()))[-4:]
                    link['toc_id'] = unique_id
                    if 'children' in link:
                        print("here2")
                        state['parentSections'][str(level)] = link['title']
                        parent = state['parentSections'].get(str(level-1), '')
                        article = ''
                        if 'link' in link:
                            print("here3")
                            article = fetch_content(link['link'])
                        full += render_section(level, unique_id, parent, link['title'], article)
                        print("here4")
                        full += append_nav(link['children'], state, level+1)
                        del state['parentSections'][str(level)]
                    else:
                        article = ''
                        if 'link' in link:
                            article = fetch_content(link['link'])
                        if article:
                            parentClass = ''
                            if not state['parentSections'].get(str(level-1)):
                                parentClass = 'noparent'
                            # if chapterise attribute exists and is true, add a section before each article
                            print("parentClass:", parentClass)
                            if 'chapterise' in doc and doc['chapterise'] or parentClass == 'noparent':
                                parent = state['parentSections'].get(str(level-1), '')
                                full += render_section(level, unique_id, parent, link['title'], "")
                            
                            
                            full += render_article(unique_id, article, parentClass)
            return full
        def render_toc(nav):
            template = env.get_template('templates/toc.html')
            return template.module.render_toc(nav)
        def render_section(level, unique_id, parent, title, article):
            print("section", level, unique_id, parent, title)
            template = env.get_template('templates/section.html')
            return template.render(level=level, unique_id=unique_id, parent=parent, title=title, article=article)
        def render_article(unique_id, article, parent):
            print("article", unique_id, parent)
            template = env.get_template('templates/article.html')
            return template.render(unique_id=unique_id, article=article, parent=parent)
        def render_html(doc):
            book = env.get_template(f'templates/book.html')
            title = doc['title']
            cover = doc['cover']
            for i in range(doc['state']['levelOffset']):
                print("here ", doc['state']['levelOffset'])
                doc['nav'] = doc['nav'][0]['children']
            with open('nav'+ doc['title'] + '.json', 'w') as f:
                f.write(json.dumps(doc['nav'], indent=2))
            inner_html = append_nav(doc['nav'], doc['state'])
            toc_section = render_toc(doc['nav'])
            return book.render(title=title, cover=cover, toc_section=toc_section, inner_html=inner_html, currentDocIntro=doc['intro'])
        for doc in self.docs:
            print(f"concatenating {doc['title']}")
            htmlfile = baseUrl + '/' + slugify_unicode(doc['title']) + '.html'
            with open(htmlfile, 'w', encoding="utf-8") as f:
                rendered_html = render_html(doc)
                f.write(rendered_html)

    def update_book_manifest(self, pdf_dir, data):
        manifest_path = os.path.join(pdf_dir, 'books.json')
        manifest_data = {}
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                try:
                    manifest_data = json.load(f)
                except json.JSONDecodeError:
                    pass # Overwrite if invalid JSON
        
        manifest_data.update(data)

        with open(manifest_path, 'w') as f:
            json.dump(manifest_data, f, indent=4)

    def create_static_viewer_files(self, pdf_dir):
        # paths relative to script dir
        viewer_html_src = os.path.join(script_dir, 'pdf_viewer.html')
        viewer_css_src = os.path.join(script_dir, 'pdf_viewer.css')
        viewer_js_src = os.path.join(script_dir, 'pdf_viewer.js')

        # paths in the output dir
        viewer_html_dest = os.path.join(pdf_dir, 'index.html')
        viewer_css_dest = os.path.join(pdf_dir, 'style.css')
        viewer_js_dest = os.path.join(pdf_dir, 'script.js')

        try:
            shutil.copy(viewer_html_src, viewer_html_dest)
            shutil.copy(viewer_css_src, viewer_css_dest)
            shutil.copy(viewer_js_src, viewer_js_dest)
            print("PDF viewer files created successfully.")
        except FileNotFoundError as e:
            print(f"Error copying viewer files: {e}. Make sure html, css, and js source files exist.")
        except Exception as e:
            print(f"An unexpected error occurred while copying viewer files: {e}")

    async def print_to_pdf(self):
        PORT = 8000
        server_directory = os.path.abspath(baseUrl)
        Handler = partial(http.server.SimpleHTTPRequestHandler, directory=server_directory)

        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            server_thread = threading.Thread(target=httpd.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            print(f"Serving on port {PORT} from {server_directory}")

            async with async_playwright() as p:
                browser = await p.chromium.launch()

                def on_console(msg):
                    print(f'Browser console: {msg.text}')

                for doc in self.docs:
                    title = slugify_unicode(doc['title'])
                    html_url = f'http://localhost:{PORT}/{title}.html'
                    pdf_dir = os.path.abspath(os.path.join(baseUrl, 'pdf'))
                    pdf_file = os.path.abspath(os.path.join(pdf_dir, f'{title}.pdf'))

                    # make sure the pdf directory exists
                    os.makedirs(pdf_dir, exist_ok=True)


                    page = await browser.new_page()

                    # Listen for console events
                    page.on('console', on_console)

                    await page.goto(html_url)

                    # Wait for the rendering to complete
                    try:
                        await page.wait_for_function('window.PAGED_RENDER_COMPLETE === true', timeout=600000)
                    except Exception as e:
                        print(f"Timeout or error waiting for rendering to complete for {html_url}: {e}")
                    
                    print(f"Printing {html_url} to {pdf_file}")
                    await page.pdf(path=pdf_file, format='A4', print_background=True)

                    # Generate thumbnail
                    jpg_file = os.path.abspath(os.path.join(pdf_dir, f'{title}.jpg'))
                    print(f"Generating thumbnail: {jpg_file}")
                    try:
                        subprocess.run([
                            'convert',
                            '-thumbnail', 'x400',
                            '-background', 'white',
                            '-alpha', 'remove',
                            '-density', '150',
                            f'{pdf_file}[0]',
                            jpg_file
                        ], check=True)

                        # Update JSON manifest
                        pdf_filename = os.path.basename(pdf_file)
                        jpg_filename = os.path.basename(jpg_file)
                        category = doc.get('base_path', 'general/').split('/')[0]

                        book_data = {
                            os.path.join(pdf_filename): {
                                "creation_time": datetime.datetime.fromtimestamp(os.path.getmtime(pdf_file)).isoformat(),
                                "thumbnail": jpg_filename,
                                "size": round(os.path.getsize(pdf_file) / (1024 * 1024), 2),
                                "category": category,
                                "title": doc['title']
                            }
                        }
                        self.update_book_manifest(pdf_dir, book_data)

                    except subprocess.CalledProcessError as e:
                        print(f"ImageMagick `convert` command failed: {e}")
                    except FileNotFoundError:
                        print("ImageMagick `convert` command not found. Please install ImageMagick.")

                    await page.close()
                await browser.close()
            
            self.create_static_viewer_files(os.path.abspath(os.path.join(baseUrl, 'pdf')))
            httpd.shutdown()

def main():
    reader = navReader(remote=False, base=baseUrl)
    reader.get_nav(docs)
    reader.concatenate_docs()
    asyncio.run(reader.print_to_pdf())


if __name__ == "__main__":
    main()
