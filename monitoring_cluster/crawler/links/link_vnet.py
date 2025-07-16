import requests
from bs4 import BeautifulSoup
import time
import datetime
from datetime import datetime
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
sys.path.append("..")

from utils.utils import connect_to_bigquery

client, table = connect_to_bigquery("neusolution", "neusolution.json", "crawler_data", "links_vnet")

BASE_URL = "https://vietnamnet.vn/"

def format_url(url):
    return url if url.startswith("http") else BASE_URL.rstrip("/") + "/" + url.lstrip("/")

def get_max_index():
    query = """
        SELECT MAX(CAST(index AS INT64)) as max_index
        FROM `neusolution.crawler_data.links_vnet`
    """
    result = client.query(query).result()
    for row in result:
        return row.max_index if row.max_index is not None else -1
    return -1
def get_links_and_texts(url, ending=None):
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve the webpage: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    links_data = []

    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        text = a.get_text(strip=True)

        if ending is None or href.endswith(ending):
            if len(text.split()) > 5:
                links_data.append({
                    "link": format_url(href),
                    "title": text,
                    'date_added': datetime.now().isoformat()
                })
    return links_data

vnet_urls = ["https://vietnamnet.vn/kinh-doanh",
       "https://vietnamnet.vn/chinh-tri",
       "https://vietnamnet.vn/thoi-su",
       "https://vietnamnet.vn/kinh-doanh",
       "https://vietnamnet.vn/thong-tin-truyen-thong",
       "https://vietnamnet.vn/the-thao",
       "https://vietnamnet.vn/giao-duc",
       "https://vietnamnet.vn/the-gioi",
       "https://vietnamnet.vn/doi-song",
    #    "https://vietnamnet.vn/giai-tri",
    #    "https://vietnamnet.vn/suc-khoe",
    #    "https://vietnamnet.vn/phap-luat",
    #    "https://vietnamnet.vn/oto-xe-may",
    #    "https://vietnamnet.vn/du-lich",
    #    "https://vietnamnet.vn/bat-dong-san",
    #    "https://vietnamnet.vn/van-hoa",
       ]




def process_url(u, i, ending):
    print(f"Fetching: {u}-page{i}")
    all_links = get_links_and_texts(f"{u}-page{i}", ending)
    if all_links:
        #
        max_index = get_max_index()
        for idx, item in enumerate(all_links):
            item['index'] = max_index + idx + 1
        #
        try:
            errors = client.insert_rows_json(table, all_links)
            if errors:
                print(f"BigQuery insert errors: {errors}")
            else:
                print(f"Inserted {len(all_links)} links into BigQuery.")
        except Exception as e:
            print(f"Error inserting into BigQuery: {e}")
    time.sleep(1)  # Prevent aggressive requests

def vnet_link_crawler( start=1, end=100, max_threads=5, ending='.html'):

    jobs = []
    for i in range(start, end):
        for u in vnet_urls:
            jobs.append((u, i))

    with ThreadPoolExecutor(max_threads) as executor:
        futures = {executor.submit(process_url, u, i, ending) for u,i in jobs}
        
        # Use tqdm to show progress of completed tasks
        for future in tqdm(as_completed(futures), total=len(futures), desc="Crawling links"):
            try:
                future.result()
            except Exception as e:
                print(f"Error processing: {e}")


if __name__ == "__main__":
    vnet_link_crawler( start=1, end=100, max_threads=len(vnet_urls), ending='.html')
