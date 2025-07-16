import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys 
sys.path.append("..")
from utils.utils import connect_to_bigquery

client, table = connect_to_bigquery("neusolution", "neusolution.json", "crawler_data", "links_tg")
BASE_URL = "https://tuyengiao.vn/"

tg_urls = [
    ('https://www.tuyengiao.vn/thoi-su-chinh-tri', 50),
    ('https://www.tuyengiao.vn/bao-ve-nen-tang-tu-tuong-cua-dang', 50),
    ('https://www.tuyengiao.vn/hoc-va-lam-theo-bac', 50),
    ('https://www.tuyengiao.vn/nhip-cau-tuyen-giao', 50),
    ('https://www.tuyengiao.vn/van-hoa-xa-hoi', 50),
    ('https://www.tuyengiao.vn/khoa-giao', 50),
    ('https://www.tuyengiao.vn/kinh-te', 50),

]

def format_url(url):
    return url if url.startswith("http") else BASE_URL.rstrip("/") + "/" + url.lstrip("/")
def get_next_index():
    """Fetch the current max index from BigQuery and return the next index."""
    query = f"SELECT MAX(`index`) as max_index FROM `{table.project}.{table.dataset_id}.{table.table_id}`"
    result = list(client.query(query))
    max_index = result[0].max_index if result and result[0].max_index is not None else -1
    return max_index + 1

def vi_get_url(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    links = soup.find_all('div', class_="clearfix")
    next_index = get_next_index()
    results = []
    for link in links:
        link = link.find_all('a')[1]
        url = link.get('href')
        title = link.get_text(strip=True)
        if url:
            # Format URL if needed
            formatted_url = format_url(url)
            if len(title.split()) > 3:
                results.append({
                    'index': next_index,
                    'link': formatted_url,
                    'title': title,
                    "date_added": datetime.now().isoformat() 
                })
                next_index += 1
            else:
                print(f"Title too short: {title}")
        else:
            print(f"Link not found in {link}")
    
    return results

def get_links_and_texts(url, ending=None):
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve the webpage: {response.status_code}")
        return []

    return vi_get_url(response.text)

def process_url(u, i, ending):
    print(f"Fetching: {u}-page{i}")
    all_links = get_links_and_texts(f"{u}?page={i}", ending)
    if all_links:
        try:
            errors = client.insert_rows_json(table, all_links)
            if errors:
                print(f"BigQuery insert errors: {errors}")
            else:
                print(f"Inserted {len(all_links)} links into BigQuery.")
        except Exception as e:
            print(f"Error inserting into BigQuery: {e}")
    time.sleep(1)  # Prevent aggressive requests

import random

def tg_link_crawler(start = 0, end = -1, max_threads=5, ending='.html'):

    jobs = []
    for u, u_end in tg_urls:
        if end > 0:
            u_end = min(u_end, end)

        for i in range(1, u_end):
            jobs.append((u, i))

    random.shuffle(jobs)

    with ThreadPoolExecutor(max_threads) as executor:
        futures = {executor.submit(process_url, u, i, ending) for u,i in jobs}

        for future in as_completed(futures):
            try:
                all_links = future.result()
            except Exception as e:
                print(f"Error processing: {e}")

    print(f"Scraping completed. Saved to MongoDB")



if __name__ == "__main__":
    tg_link_crawler(start = 0, end = 3, max_threads=5, ending='.html')