import requests
from bs4 import BeautifulSoup
import json
import time
import os
import pymongo
from datetime import datetime
import sys 
sys.path.append("..")
from utils.utils import connect_to_bigquery
from concurrent.futures import ThreadPoolExecutor, as_completed            


vtc_urls = [
    "https://vtcnews.vn/kinh-te-29.html",
    "https://vtcnews.vn/the-thao-34.html",
    "https://vtcnews.vn/giao-duc-31.html",
    "https://vtcnews.vn/gia-dinh-78.html",
    "https://vtcnews.vn/phap-luat-32.html",
    "https://vtcnews.vn/giai-tri-33.html",
    "https://vtcnews.vn/khoa-hoc-cong-nghe-82.html",
    "https://vtcnews.vn/suc-khoe-35.html",
    "https://vtcnews.vn/oto-xe-may-37.html",
    "https://vtcnews.vn/song-xanh-266.html",
    "https://vtcnews.vn/the-gioi-30.html",
    ]


client, table = connect_to_bigquery("neusolution", "neusolution.json", "crawler_data", "links_vtc")
def get_max_index():
    query = """
        SELECT MAX(CAST(index AS INT64)) as max_index
        FROM `neusolution.crawler_data.links_vtc`
    """
    result = client.query(query).result()
    for row in result:
        return row.max_index if row.max_index is not None else -1
    return -1

def get_links_and_texts(url,ending=None):
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve the webpage: {response.status_code}")
    soup = BeautifulSoup(response.text, 'html.parser')
    links_data = []
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        text = a.get_text(strip=True)
        if not href.startswith("http"):
            href = f"https://vtcnews.vn{href}"
        if ending is None or href.endswith(ending):
            if len(text.split()) > 5:
                links_data.append({
                    "link": href,
                    "title": text,
                    "date_added": datetime.now().isoformat() 
                })
    return links_data

def process_url(u, i, ending):
    if u.endswith(ending):
        u = u.replace(ending, f"/trang-{i}{ending}")
    print(f"Fetching: {u}")
    all_links = get_links_and_texts(u, ending)
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
    time.sleep(1)    # Prevent aggressive requests

def vtc_link_crawler(start=2, end=10, max_threads=5, ending='.html'):
    jobs = []
    for i in range(start, end):
        for u in vtc_urls:
            jobs.append((u, i))

    with ThreadPoolExecutor(max_threads) as executor:
        futures = {executor.submit(process_url, u, i, ending) for u,i in jobs}

        for future in as_completed(futures):
            try:
                all_links = future.result()
                # pages.update(all_links)
            except Exception as e:
                print(f"Error processing: {e}")

if __name__ == "__main__":
    vtc_link_crawler(start=1, end=5, max_threads=5, ending='.html')
