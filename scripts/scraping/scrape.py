import os
import requests
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from traceback import print_exc
import json
import re


def download_page(url, content, path):
    """Downloads a web page and saves it to a file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w+', encoding='utf8') as f:
        f.write(content)
    print('Saving ' + path)


def download_resource(url, path, save_to):
    """Downloads a resource (CSS, JS, image, etc.) and saves it to a file."""
    if url.endswith('.com') or url.endswith('.ca'):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    content = requests.get(
        url,
        headers={'Origin': 'https://' + urlparse(url).hostname}
    ).content
    try:
        if '.js' in url:
            content = content.decode('utf8')
            content = content.replace('https://' + urlparse(url).hostname, os.path.abspath(save_to).replace('\\', '/').split(':', 1)[1])
            content = re.sub(r'"/?(.*).svg"', os.path.abspath(save_to).replace('\\', '/').split(':', 1)[1] + '/resources/\\1.svg', content)
            content = content.encode('utf8')
        with open(path, 'wb') as f:
            f.write(content)
        print('    Saving ' + path)
    except:
        # print_exc()
        return


def download_pdfs_in_html(soup, url, save_to):
    """function to find all links in an HTML page that point to PDF files and convert each PDF to HTML"""
    # find all links in the HTML page
    for link in soup.find_all("a"):
        # check if the link points to a PDF file
        if link.get("href") and link.get("href").endswith(".pdf"):
            pdf_url = urljoin(url, link.get("href"))
            print(f"Converting {pdf_url} to HTML...")
            pdf_to_html(pdf_url, save_to)


def pdf_to_html(pdf_url, save_to):
    """function to download a PDF file and convert it to HTML using pdf2htmlEX"""
    # https://github.com/coolwanglu/pdf2htmlEX/wiki/Download
    # download the PDF file
    response = requests.get(pdf_url)
    filename = os.path.join(save_to, 'pdfs', urlparse(pdf_url).path.lstrip('/'))
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "wb") as f:
        f.write(response.content)
    with open(filename.replace('.pdf', '.meta.json'), "w+") as f:
        f.write(json.dumps({'url': pdf_url}))

    # convert the PDF file to HTML using pdf2htmlEX
    exe = 'pdf2htmlEX/pdf2htmlEX.exe'
    os.system(f'""{exe}" "{os.path.abspath(filename)}" --no-drm=1 --optimize-text=1 --process-outline=0 --dest-dir="{os.path.dirname(os.path.abspath(filename))}""')

    # remove the original PDF file
    # os.remove(filename)


def scrape_url(args):
    # Create a new browser instance
    driver = webdriver.Edge()

    try:
        (i, total, url, save_to) = args

        print(f'Processing ({i}/{total}) {url}')

        # Navigate to the URL
        driver.get(url)

        # Wait for the page to finish loading
        driver.implicitly_wait(9)

        # Get the page source of current DOM
        page_source = driver.page_source

        # Download the page
        page_path = os.path.join(save_to, urlparse(url).path.lstrip('/'))
        if page_path[-1] == '/':
            page_path = page_path[:-1]
        page_path += '.html'
        download_page(url, page_source, page_path)

        # Parse the HTML
        with open(page_path, 'rb') as f:
            soup = BeautifulSoup(f, 'html.parser')

        title = soup.find('title')
        with open(page_path.replace('.html', '.meta.json'), 'w+', encoding='utf8') as f:
            f.write(json.dumps({'url': url, 'title': title.text}))

        download_pdfs_in_html(soup, url, save_to)

        # Download and replace resources in the HTML
        resources = soup.find_all(['link', 'script', 'img'])
        for res in resources:
            if 'src' in res.attrs:
                res_url = urljoin(url, res['src'])
            elif 'href' in res.attrs:
                res_url = urljoin(url, res['href'])
            else:
                continue

            res_path = os.path.join(save_to, 'resources', urlparse(res_url).path.lstrip('/'))
            if not os.path.isfile(res_path):
                download_resource(res_url, res_path, save_to)

            if 'src' in res.attrs:
                res.attrs['src'] = os.path.abspath(res_path).replace('\\', '/').split(':', 1)[1]
            elif 'href' in res.attrs:
                res.attrs['href'] = os.path.abspath(res_path).replace('\\', '/').split(':', 1)[1]

        # Save the modified HTML
        with open(page_path, 'wb') as f:
            f.write(soup.encode())
    except:
        print_exc()
        return
    finally:
        # Close the browser
        driver.quit()


def scrape_sitemap(sitemap, save_to='../../data/BMOcomCloned'):
    """Clones all pages in the sitemap and saves them along with their resources as local copies."""
    urls = list(sitemap.keys())

    with ThreadPoolExecutor(max_workers=16) as executor:
        total = len(urls)
        futures = [executor.submit(scrape_url, (i, total, url, save_to)) for i, url in enumerate(urls)]

        # Wait for all the futures to complete
        for future in futures:
            future.result()

    for url, sub_sitemap in sitemap.items():
        try:
            # Recursively clone sub-sitemap
            if sub_sitemap:
                scrape_sitemap(sub_sitemap, save_to)
        except:
            continue

