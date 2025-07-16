import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed            
sys.path.append("..")
from utils.utils import connect_to_bigquery
urls = [
    "https://vnexpress.net/the-thao",
    "https://vnexpress.net/thoi-su",
    "https://vnexpress.net/giao-duc",
    "https://vnexpress.net/kinh-doanh",
    "https://vnexpress.net/doi-song",
    "https://vnexpress.net/the-gioi",
    "https://vnexpress.net/giai-tri",
    "https://vnexpress.net/suc-khoe",
    "https://vnexpress.net/phap-luat",
    "https://vnexpress.net/cong-nghe",
    "https://vnexpress.net/khoa-hoc",
    "https://vnexpress.net/bat-dong-san",
    "https://vnexpress.net/oto-xe-may",
    "https://vnexpress.net/du-lich",
    "https://vnexpress.net/y-kien",
    ]

client, table = connect_to_bigquery("neusolution", "neusolution.json", "crawler_data", "links_vnex")

def get_max_index():
    query = """
        SELECT MAX(CAST(index AS INT64)) as max_index
        FROM `neusolution.crawler_data.links_vnex`
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
        if ending is None or href.endswith(ending):
            if len(text.split()) > 5:
                links_data.append({
                    "link": href,
                    "title": text,
                    "date_added": datetime.now().isoformat()
                })
    return links_data


def process_url(u, i, ending):
    print(f"Fetching: {u}-p{i}")
    all_links = get_links_and_texts(f"{u}-p{i}", ending)
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

def main(urls, start=2, end=10, max_threads=5, ending='.html'):
    jobs = []
    for i in range(start, end):
        for u in urls:
            jobs.append((u, i))

    with ThreadPoolExecutor(max_threads) as executor:
        futures = {executor.submit(process_url, u, i, ending) for u,i in jobs}

        for future in as_completed(futures):
            try:
                all_links = future.result()
                # pages.update(all_links)
            except Exception as e:
                print(f"Error processing: {e}")

main(urls, start=1, end=5, max_threads=10, ending='.html')
