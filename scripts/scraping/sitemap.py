import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import json


total_links = 0


def get_robots_txt(url):
    """
    This function downloads the robots.txt file of a website given its URL.
    """
    parsed_url = urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
    response = requests.get(robots_url)
    return response.text


def get_sitemap_links(robots_txt):
    """
    This function extracts the sitemap URLs from the robots.txt file.
    """
    sitemap_links = []
    for line in robots_txt.split('\n'):
        if 'sitemap:' in line.lower():
            sitemap_links.append(line.split()[-1])
    return sitemap_links


def get_links_from_sitemap(sitemap_url, max_depth=1, depth=0, filter_func=lambda l:True):
    """
    This function recursively reads all the links in a sitemap and builds a sitemap hierarchy up to a certain depth.
    """
    if depth >= max_depth:
        return

    response = requests.get(sitemap_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    urls = []
    for loc in soup.find_all('loc'):
        urls.append(loc.text)

    sitemap = {}
    urls = list(filter(filter_func, urls))
    for url in urls:
        if url.endswith('.xml'):
            sub_sitemap = get_links_from_sitemap(url, max_depth, depth + 1)
            if sub_sitemap:
                sitemap[url] = sub_sitemap
        else:
            sitemap[url] = None

    global total_links
    total_links += len(urls)
    return sitemap


def generate_html_tree(sitemap, depth=0, save_to='D:\\'):
    """
    This function generates an HTML representation of the sitemap hierarchy as a collapsible tree.
    """
    if not sitemap:
        return ''

    if depth == 0:
        html = '<ul style="display:block">'
    else:
        html = '<ul>'
    for url, sub_sitemap in sitemap.items():
        url_cache = os.path.join(save_to, urlparse(url).path.lstrip('/'))
        if url_cache[-1] == '/':
            url_cache = url_cache[:-1]
        txt_cache = url_cache + '.txt'
        url_cache += '.html'
        html += f'<li class="collapsed"><span class="link" data-href="{url_cache}">(Cache) </span><span class="link" data-href="{txt_cache}">(Extracted Text) </span><span class="link" data-href="{url}">{url}</span></li>'
        if sub_sitemap:
            html += generate_html_tree(sub_sitemap, depth=depth + 1, save_to=save_to)
    html += '</ul>'

    if depth == 0:
        html = f'<div class="sitemap">{html}</div>'

    return html


def build_sitemap(url='https://www.bmo.com', max_depth=3, save_to='../../data/BMOcomCloned', filter_func=lambda l:not '/en-us/' in l):
    robots_txt = get_robots_txt(url)
    sitemap_links = get_sitemap_links(robots_txt)

    sitemap = {}
    for sitemap_link in sitemap_links:
        sub_sitemap = get_links_from_sitemap(sitemap_link, max_depth, filter_func=filter_func)
        if sub_sitemap:
            sitemap[sitemap_link] = sub_sitemap

    with open(os.path.join(save_to, 'sitemap.json'), 'w+') as f:
        f.write(json.dumps(sitemap))

    html = generate_html_tree(sitemap, save_to=save_to)
    with open(os.path.join(save_to, 'sitemap.html'), 'w') as f:
        f.write(f'''
        <html>
            <head>

                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css" 
                crossorigin="anonymous" referrerpolicy="no-referrer" />

                <title>Sitemap</title>
                <style>
                    ul {{
                        list-style-type: none;
                        margin: 0;
                        padding: 0;
                    }}
    
                    .sitemap ul {{
                        display: none;
                        margin-left: 1em;
                    }}
    
                    .sitemap li {{
                        cursor: pointer;
                    }}
    
                    .sitemap li:before {{
                        content: "-";
                        display: inline-block;
                        margin-right: 0.5em;
                    }}
    
                    .sitemap li.collapsed:before {{
                        content: "+";
                    }}
                </style>
            </head>
            <body>
                {html}
                <script>

                    document.querySelectorAll(".sitemap li").forEach(c => {{
                        c.addEventListener("click", () => {{
                            c.classList.toggle("collapsed");
                            var ul = c.nextElementSibling;
                            if (ul.tagName.toLowerCase() === "ul") {{
                                if (c.classList.contains("collapsed")) {{
                                    ul.style.display = "none";
                                }} else {{
                                    ul.style.display = "block";
                                }}
                            }}
                        }})
                    }})

                    document.querySelectorAll(".sitemap li .link").forEach(l => {{
                        l.addEventListener("click", e => {{
                            window.open(l.getAttribute ('data-href'), '_blank');
                            e.stopPropagation();
                        }})
                    }})
                </script>
            <p>Total links: {total_links}</p>
            </body>
        </html>
        ''')
    print("Sitemap generated and saved to sitemap.html!")
    return sitemap

