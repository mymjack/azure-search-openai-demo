
import glob
from bs4 import BeautifulSoup, Comment
import os
import json


def extract_html(soup, depth=0, purge_tags=[]):
    if not soup:
        return ' '
    result = ""
    is_mixed_content = len(soup.contents) > 1
    if depth == 13:
        print('her')
    for element in soup.contents:
        if isinstance(element, Comment):
            continue
        if element.name in (['script', 'style', 'head', 'title', 'meta', 'link'] + purge_tags):
            continue
        if element.name == 'br':
            result += '\n'

        elif element.name in ['a', 'strong', 'b', 'em', 'i', 'u', 'span']:
            result += ' ' + extract_html(element, depth+1, purge_tags)
        elif element.name in ['img']:
            if element.has_attr('alt'):
                result += ' ' + element['alt']
            # is_mixed_content = True
        elif isinstance(element, str):
            result += ' ' + element
            # is_mixed_content = True
        else:
            result += ' ' + extract_html(element, depth+1, purge_tags)

    result = result.strip()
    is_mixed_content &= result != ''
    if is_mixed_content:
        return f'<{depth}>' + result + f'</{depth}>'
    else:
        return result


def purge_from_soup(soup, tags):
    for t in tags:
        component = soup.find(t)
        if component:
            component.decompose()


def extract_all_html(save_to="../../data/BMOcomCloned", skip_header_footer=True):
    html_files = glob.glob(os.path.join(save_to, "**/*.html"), recursive=True)

    # loop through the list of HTML files
    total = len(html_files)
    for i, file in enumerate(html_files):
        with open(file, 'rb') as html_file:
            print(f'Processing ({i}/{total}) {file}')
            soup = BeautifulSoup(html_file, 'html.parser')
            purge_tags = ['header', 'footer', 'nav'] if skip_header_footer else []
            text = extract_html(soup.body, purge_tags=purge_tags)

        with open(file.replace('.html', '.txt'), 'w+', encoding='utf-8') as f:
            if 'pdf' in file:
                # PDF only whitespace fix
                text = text.replace('  ', '')
            f.write(text)


