
from markdown.treeprocessors import Treeprocessor
from markdown.extensions import Extension
from PIL import Image
import os
import requests
from io import BytesIO
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

class D_MaxWidth(Extension):
    def extendMarkdown(self, md):
        # Register the custom Treeprocessor with the Markdown instance
        md.treeprocessors.register(ImageMaxWidthProcessor(self), 'd_maxwidth', 10)

class ImageMaxWidthProcessor(Treeprocessor):
    def run(self, root: ET.Element):
        
        # print the current document location if possible
        if hasattr(self, 'source_position'):
            print(f"Processing document: {self.source_position}.")
        print(f"Processing root: {root}.")

        for img in root.findall('.//img'):
            src = img.get('src')
            # print(f"Processing element: {src}.")
            if src:
                try:
                    if self.is_url(src):
                        print(f"Processing URL: {src}.")
                        return None
                        img_data = self.download_image(src)
                        if img_data:
                            self.set_image_max_width(img, img_data)
                    elif os.path.exists(src):
                        print(f"Processing local file: {src}.")
                        with Image.open(src) as im:
                            width, _ = im.size
                            # Ensure width is an integer
                            width = int(width)
                            img.set('style', f'max-width:{width}px;')
                            print(f"Processed image: {src}. Width: {width}. img: {img}.")
                except Exception as e:
                    print(f"Exception processing image {src}: {e}")
                print(f"Processed image: {src}.")

    def is_url(self, src):
        # Check if the source is a URL
        parsed_url = urlparse(src)
        # Consider it a URL if the scheme and netloc parts are present
        return bool(parsed_url.scheme and parsed_url.netloc)

    def download_image(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return BytesIO(response.content)
        except requests.RequestException as e:
            print(f"Failed to download image {url}: {e}")
            return None

    def set_image_max_width(self, img, img_data):
        try:
            with Image.open(img_data) as im:
                width, _ = im.size
                # Ensure width is an integer
                width = int(width)
                img.set('style', f'max-width:{width}px;')
        except Exception as e:
            print(f"Cannot open image data: {e}")


def makeExtension(**kwargs):
    return D_MaxWidth(**kwargs)


