import requests
from bs4 import BeautifulSoup
from datetime import datetime
from tqdm import tqdm

import sys 
sys.path.append("..")
from utils.utils import connect_to_bigquery

client, table = connect_to_bigquery("neusolution", "neusolution.json", "crawler_data", "links_nd")

BASE_URL = "https://en.nhandan.vn/"

vi_zone = [1171, 1176, 1180, 1185, 1191, 1203, 1251, 1121, 1122, 1319, 1287, 1257, 1231,704471, 704476, 704475, 704474, 704473, 704472, 1224, 1303, 1309, 1311, 1292, 1296, 1315]
en_zone = [1,15, 16, 809, 13, 18, 803, 2, 804, 805, 3, 22, 23, 24, 4, 806, 25, 32, 5, 28, 29, 6, 807, 31, 7, 33, 34, 35, 36, ]
cn_zone = [36, 52, 44, 45, 46, 53, 54, 55, 82, 56, 57, 59, 58, 83, 48, 49 , 71, 72, 301]
fr_zone = [71, 171, 271, 371, 871, 1071, 1371, 471]
def get_next_index():
    """Fetch the current max index from BigQuery and return the next index."""
    query = f"SELECT MAX(`index`) as max_index FROM `{table.project}.{table.dataset_id}.{table.table_id}`"
    result = list(client.query(query))
    max_index = result[0].max_index if result and result[0].max_index is not None else -1
    return max_index + 1
def format_url(url, base_url = BASE_URL):
    return url if url.startswith("http") else base_url.rstrip("/") + "/" + url.lstrip("/")


def fecth_api(url, base_url = BASE_URL):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(format_url(url, base_url), headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch page, status code: {response.status_code}")
        return None


def vi_get_url(html_content, base_url = BASE_URL):
    soup = BeautifulSoup(html_content, 'html.parser')
    links = soup.find_all('a', class_="cms-link")
    next_index = get_next_index()
    results = []
    for link in links:
        url = link.get('href')
        title = link.get_text(strip=True)
        if url:
            # Format URL if needed
            formatted_url = format_url(url, base_url)
            if len(title.split()) > 3:
                results.append({
                    'index': next_index,
                    'link': formatted_url,
                    'title': title,
                    'date_added': datetime.now().isoformat(),
                    'base_url': base_url,
                    'lang': 'vi'
                })
                next_index += 1
        else:
            print(f"Link not found in {link}")
    return results

def process_single_page(root, base_url = BASE_URL):
    
    for l in tqdm(range(1, 101)):
        # time.sleep(1)
        url = root.format(i = l)
        # print(f"Processing {url}")
        data = fecth_api(url, base_url)
        
        if data.get('error_code') == 0:
            content = data['data']['articles']
            result = vi_get_url(content, base_url)
            if result:
                try:
                    errors = client.insert_rows_json(table, result)
                    if errors:
                        print(f"BigQuery insert errors: {errors}")
                    else:
                        print(f"Inserted {len(result)} links into BigQuery.")
                except Exception as e:
                    print(f"Error inserting into BigQuery: {e}")
        else: 
            break

def process_single_page_en(root, start = 1, end = 100, lang = 'vi', base_url = BASE_URL):
    next_index = get_next_index()
    for l in tqdm(range(start, end)):
        # time.sleep(1)
        url = root.format(i = l)
        data = fecth_api(url, base_url)    
            
        if data.get('error_code') == 0:
            content = data['data']['contents']
            valid_links = []
            for c in content:
                title = c.get('title')
                url = c.get('url')
                if url:
                    full_url = format_url(url, base_url)
                    valid_links.append({
                        'index': next_index,
                        'link': full_url,
                        'title': title,
                        'date_added': datetime.now().isoformat(),
                        'base_url': base_url,
                        'lang': lang
                    })
                    next_index += 1
            if valid_links:
                try:
                    errors = client.insert_rows_json(table, valid_links)
                    if errors:
                        print(f"BigQuery insert errors at page {l}: {errors}")
                    else:
                        print(f"Inserted {len(valid_links)} links into BigQuery from page {l}.")
                except Exception as e:
                    print(f"Error inserting into BigQuery at page {l}: {e}")
        else:
            print(f"Non-zero error_code at page {l}, stopping.")
            break

def nd_link_crawler_vi(start=1, end=10, **kwargs):
    api_url = 'https://nhandan.vn/api/morenews-zone-{zone}-{i}.html?phrase=&t'
    
    root_urls = []
    for zone in vi_zone:
        root_urls.append(api_url.format(zone=zone, i="{i}"))

    for url in root_urls:
        process_single_page(url)

def nd_link_crawler_en(start=1, end=10, **kwargs):
    api_url = 'https://api-en.nhandan.vn/api/morenews-zone-{zone}-{i}.html?phrase='
    
    root_urls = []
    for zone in en_zone:
        root_urls.append(api_url.format(zone=zone, i="{i}"))

    for url in root_urls:
        process_single_page_en(url, start, end, lang='en', base_url = 'https://en.nhandan.vn/')


def nd_link_crawler_cn(start=1, end=10, **kwargs):
    api_url = 'https://api-cn.nhandan.vn/api/morenews-zone-{zone}-{i}.html?phrase='
    
    root_urls = []
    for zone in cn_zone:
        root_urls.append(api_url.format(zone=zone, i="{i}"))

    for url in root_urls:
        process_single_page_en(url, start, end, lang='cn', base_url = 'https://cn.nhandan.vn/')

def nd_link_crawler_fr(start=1, end=10, **kwargs):
    api_url = 'https://api-fr.nhandan.vn/api/morenews-zone-{zone}-{i}.html?phrase='
    
    root_urls = []
    for zone in fr_zone:
        root_urls.append(api_url.format(zone=zone, i="{i}"))

    for url in root_urls:
        process_single_page_en(url, start, end, lang='fr', base_url = 'https://fr.nhandan.vn/')

if __name__ == '__main__':
    nd_link_crawler_en(start=1, end=2)
    nd_link_crawler_fr(start=1, end=2)
    nd_link_crawler_cn(start=1, end=2)