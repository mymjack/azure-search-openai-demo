import os
from scripts.scraping.sitemap import build_sitemap
from scripts.scraping.scrape import scrape_sitemap
from scripts.scraping.extract import extract_all_html

if __name__ == '__main__':
    os.makedirs('../../data/BMOcomCloned', exist_ok=True)
    save_to = '../../data/BMOcomCloned'
    sitemap = build_sitemap('https://www.bmo.com',
                  max_depth=3,
                  save_to=save_to,
                  filter_func=lambda l: not '/en-us/' in l)
    # sitemap = {
    #     'https://www.bmo.com/main/personal/bank-accounts/': None
    # }
    scrape_sitemap(sitemap, save_to, save_resources=False)
    extract_all_html(save_to, skip_header_footer=True, condense_content=True)