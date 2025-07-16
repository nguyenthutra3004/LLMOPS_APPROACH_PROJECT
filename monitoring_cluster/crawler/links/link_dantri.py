# import requests
# from bs4 import BeautifulSoup
# import json
# import time
# import os
# from urllib.parse import urljoin, urlparse
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from datetime import datetime
# import sys 
# sys.path.append("..")
# from utils.utils import (
#     connect_to_bigquery
# )

# client, table = connect_to_bigquery("neusolution", "neusolution.json", "crawler_data", "links_dantri")


# # Danh sách URL cần crawl
# dantri_urls = [
#     "https://dantri.com.vn/kinh-doanh.htm",
#     "https://dantri.com.vn/the-thao.htm",
#     "https://dantri.com.vn/xa-hoi.htm",
#     "https://dantri.com.vn/the-gioi.htm",
#     "https://dantri.com.vn/giai-tri.htm",
#     "https://dantri.com.vn/bat-dong-san.htm",
#     "https://dantri.com.vn/suc-khoe.htm",
#     "https://dantri.com.vn/noi-vu.htm",
#     "https://dantri.com.vn/o-to-xe-may.htm",
#     "https://dantri.com.vn/giao-duc.htm",
#     "https://dantri.com.vn/phap-luat.htm",
#     "https://dantri.com.vn/cong-nghe.htm",
#     "https://dantri.com.vn/lao-dong-viec-lam.htm",
# ]

# BASE_URL = "https://dantri.com.vn/"

# # Hàm lấy liên kết và tiêu đề từ một trang
# def get_links_and_texts(url, ending=".htm"):
#     print("___")
#     response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    
#     if response.status_code != 200:
#         print(f"Failed to retrieve {url}: {response.status_code}")
#         return []
    
#     soup = BeautifulSoup(response.text, 'html.parser')

#     links_data = []
#     for a in soup.find_all('a', href=True):
#         href = a['href'].strip()
#         text = a.get_text(strip=True)

#         # Chuẩn hóa URL (chuyển relative URL thành absolute URL)
#         full_url = urljoin(url, href)

#         # Lọc URL theo điều kiện
#         if (ending is None or full_url.endswith(ending)) and len(text.split()) > 5:
#             links_data.append({
#                 "link": full_url,
#                 "title": text,
#                 "date_added": datetime.now().isoformat()
#             })
    
#     return links_data


# # Hàm xử lý từng trang
# def process_url(base_url, page_number, ending):
#     # Xử lý URL: bỏ ".htm" để ghép trang đúng   
#     parsed_url = urlparse(base_url)
#     clean_path = parsed_url.path.replace(".htm", "")  # Loại bỏ phần mở rộng ".htm"
#     page_url = f"{parsed_url.scheme}://{parsed_url.netloc}{clean_path}/trang-{page_number}.htm"
#     print(f"Fetching: {page_url}")
#     all_links = get_links_and_texts(page_url, ending)
#     if not all_links:
#         print(f"No links found in: {page_url}")
#     valid_links = [link for link in all_links if BASE_URL in link["link"]]

#     # Insert BigQuery ( batch)
#     if valid_links:
#         try:
#             errors = client.insert_rows_json(table, valid_links)
#             if errors:
#                 print(f"BigQuery insert errors: {errors}")
#             else:
#                 print(f"Inserted {len(valid_links)} links into BigQuery.")
#         except Exception as e:
#             print(f"Error inserting into BigQuery: {e}")

#     time.sleep(1)  
#     return all_links

# # Hàm chính để chạy scraping
# def dantri_link_crawler(start=1, end=2, max_threads=5, ending=".htm"):
#     jobs = [(u, i) for u in dantri_urls for i in range(start, end)]

#     with ThreadPoolExecutor(max_threads) as executor:
#         futures = {executor.submit(process_url, u, i, ending): (u, i) for u, i in jobs}

#         for future in as_completed(futures):
#             try:
#                 _ = future.result()
#             except Exception as e:
#                 print(f"Error processing {futures[future]}: {e}")

#     print(f"Scraping completed. Saved to BQ")

# if __name__ == "__main__":
#     dantri_link_crawler(start=1, end=100, max_threads=5)

import requests
from bs4 import BeautifulSoup
import time
import threading
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import sys 
sys.path.append("..")
from utils.utils import (
    connect_to_bigquery
)

client, table = connect_to_bigquery("neusolution", "neusolution.json", "crawler_data", "links_dantri")

dantri_urls = [
    "https://dantri.com.vn/kinh-doanh.htm",
    "https://dantri.com.vn/the-thao.htm",
    "https://dantri.com.vn/xa-hoi.htm",
    "https://dantri.com.vn/the-gioi.htm",
    "https://dantri.com.vn/giai-tri.htm",
    "https://dantri.com.vn/bat-dong-san.htm",
    "https://dantri.com.vn/suc-khoe.htm",
    "https://dantri.com.vn/noi-vu.htm",
    "https://dantri.com.vn/o-to-xe-may.htm",
    "https://dantri.com.vn/giao-duc.htm",
    "https://dantri.com.vn/phap-luat.htm",
    "https://dantri.com.vn/cong-nghe.htm",
    "https://dantri.com.vn/lao-dong-viec-lam.htm",
]

BASE_URL = "https://dantri.com.vn/"

def get_max_index():
    query = """
        SELECT MAX(CAST(index AS INT64)) as max_index
        FROM `neusolution.crawler_data.links_dantri`
    """
    result = client.query(query).result()
    for row in result:
        return row.max_index if row.max_index is not None else -1
    return -1

def get_links_and_texts(url, ending=".htm"):
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if response.status_code != 200:
        print(f"Failed to retrieve {url}: {response.status_code}")
        return []
    soup = BeautifulSoup(response.text, 'html.parser')
    links_data = []
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        text = a.get_text(strip=True)
        full_url = urljoin(url, href)
        if (ending is None or full_url.endswith(ending)) and len(text.split()) > 5:
            links_data.append({
                "link": full_url,
                "title": text,
                "date_added": datetime.now().isoformat()
            })
    return links_data

def process_url(base_url, page_number, ending, index_counter, counter_lock):
    parsed_url = urlparse(base_url)
    clean_path = parsed_url.path.replace(".htm", "")
    page_url = f"{parsed_url.scheme}://{parsed_url.netloc}{clean_path}/trang-{page_number}.htm"
    print(f"Fetching: {page_url}")
    all_links = get_links_and_texts(page_url, ending)
    if not all_links:
        print(f"No links found in: {page_url}")
    valid_links = [link for link in all_links if BASE_URL in link["link"]]
    # Assign unique index to each link
    with counter_lock:
        start_index = index_counter[0] + 1
        index_counter[0] += len(valid_links)
        for i, link in enumerate(valid_links):
            link["index"] = start_index + i
    # Insert BigQuery (batch)
    if valid_links:
        try:
            errors = client.insert_rows_json(table, valid_links)
            if errors:
                print(f"BigQuery insert errors: {errors}")
            else:
                print(f"Inserted {len(valid_links)} links into BigQuery.")
        except Exception as e:
            print(f"Error inserting into BigQuery: {e}")
    time.sleep(1)
    return valid_links

def dantri_link_crawler(start=1, end=2, max_threads=5, ending=".htm"):
    jobs = [(u, i) for u in dantri_urls for i in range(start, end)]
    latest_index = get_max_index()
    index_counter = [latest_index]  # Use list for mutability in threads
    counter_lock = threading.Lock()
    with ThreadPoolExecutor(max_threads) as executor:
        futures = {
            executor.submit(process_url, u, i, ending, index_counter, counter_lock): (u, i)
            for u, i in jobs
        }
        for future in as_completed(futures):
            try:
                _ = future.result()
            except Exception as e:
                print(f"Error processing {futures[future]}: {e}")
    print(f"Scraping completed. Saved to BQ")

if __name__ == "__main__":
    dantri_link_crawler(start=1, end=5, max_threads=5)