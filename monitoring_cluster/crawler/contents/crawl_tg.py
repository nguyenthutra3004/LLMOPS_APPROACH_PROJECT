from bs4 import BeautifulSoup
import pymongo
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys 
import random
import time
sys.path.append("..")
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from utils.utils import (
    fulltext_to_markdown,
    parse_vietnamese_datetime,
    connect_to_bigquery,
    multithreaded_crawl_bq
)

def parse_page_tg(html):
    soup = BeautifulSoup(html, 'html.parser')
    body = soup.find('body')
    text_time = ""

    content = body.find('div', class_='flex-fill')
    if content is None:
        return None

    try:
        title  = body.find('h1', class_='story-headline')
        tldr = content.find('div', class_='story-teaser')

        # content = content.find('div', class_='main-col')

        # Get time
        time = content.find('div', class_='ml-lg-auto')
        if time is not None:
            text_time = time.text
            text_time = text_time.strip()
            time.decompose()

        content = content.find('div', class_='story-body')

        for img in content.find_all('img'):
            img.decompose()

        for figure in content.find_all('figure'):
            figure.decompose()

        for table in content.find_all('table', class_='picture'):
            table.decompose()

        text  = fulltext_to_markdown(content.prettify())
        
        title = fulltext_to_markdown(title.prettify())

        tldr = fulltext_to_markdown(tldr.prettify())

        time_text = text_time.get_text(strip=True) if text_time else ""
        full_text = f"{title}\n\n{tldr}\n\n{text}"
        is_err_link = not text or not time_text
        return {
            "time": time_text,
            "content": full_text.strip(),
            "is_err_link": is_err_link  # True = có lỗi, False = không có lỗi
        }
    except Exception as e:
        print(f"Error: {e}")
        return None

# Main
if __name__ == "__main__":
    client, table = connect_to_bigquery("neusolution", "neusolution.json", "crawler_data", "links_tg")
    multithreaded_crawl_bq(client, table, parse_page_tg, max_threads=4,limit=None)