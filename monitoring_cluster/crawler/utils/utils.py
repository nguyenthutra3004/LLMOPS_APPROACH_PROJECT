import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import re
import html2text
from fake_headers import Headers
import time
import random
from pymongo import MongoClient
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import dotenv
dotenv.load_dotenv()
from typing import Callable, Dict, Any
from google.cloud import bigquery
header = Headers(
        browser="chrome",  # Generate only Chrome UA
        os="win",  # Generate ony Windows platform
        headers=True  # generate misc headers
    )
current_dir = os.path.dirname(os.path.abspath(__file__))
credentials_path = os.path.join(current_dir, "neusolution.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
import datetime
import re

def connect_to_mongo(uri = None, username = None, password = None, db_name=None, collection_name=None):
    try:
        if uri is None:
            uri = os.getenv('MONGODB_URI')
        if username is None:
            username = os.getenv('MONGODB_USERNAME')
        if password is None:
            password = os.getenv('MONGODB_PASSWORD')

        client = MongoClient(uri, username=username, password=password, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')  # Kiểm tra kết nối
        print("MongoDB connection successful")

        if collection_name and db_name:
            db = client[db_name]
            collection = db[collection_name]
            return collection
        
        return client[db_name] if db_name else client
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return None
from pathlib import Path
def connect_to_bigquery(project_id=None, credentials_path=None, dataset_name=None, table_name=None):
    """
    Kết nối tới Google BigQuery.

    Params:
        project_id (str): ID của project GCP. Nếu không truyền vào, sẽ lấy từ biến môi trường `GCP_PROJECT_ID`.
        credentials_path (str): Đường dẫn tới file JSON credentials. Nếu không truyền vào, sẽ lấy từ `GOOGLE_APPLICATION_CREDENTIALS`.

    Returns:
        bigquery.Client hoặc None nếu thất bại.
    """
    if credentials_path:
        cred = Path(credentials_path)
        if not cred.is_absolute():
            # __file__ ở utils/utils.py, lấy thư mục chứa file này
            base = Path(__file__).resolve().parent
            cred = base / credentials_path
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred)

    # Lấy project_id từ param hoặc env
    #if project_id is None:
        #project_id = os.getenv("GCP_PROJECT_ID")
    project_id = "neusolution"

    try:
        client = bigquery.Client(project=project_id)
        client.query("SELECT 1").result()
        print("BigQuery connection successful")
        if dataset_name and table_name:
            table_ref = f"{project_id}.{dataset_name}.{table_name}"
            table = client.get_table(table_ref)
            # df = client.query(f"SELECT * FROM `{table_ref}` LIMIT 1").to_dataframe()
            # print(df)
            return client, table

        elif dataset_name:
            dataset = client.get_dataset(f"{project_id}.{dataset_name}")
            print(f"Dataset `{dataset.dataset_id}` loaded.")
            return client, dataset

        return client, None
    except Exception as e:
        print(f"BigQuery connection failed: {e}")
        return None,None

    
def parse_vietnamese_datetime(time_str):
    """
    Parse a Vietnamese date time string like "Thứ sáu, ngày 25/04/2025 - 11:39"
    into a datetime object
    """
    try:
        # Format: "Thứ sáu, ngày 25/04/2025 - 11:39"
        vn_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', time_str)
        if vn_match:
            date_str = vn_match.groups()[0]
            day, month, year = map(int, date_str.split('/'))

            return datetime.datetime(year, month, day)
        
        # Try other common formats if needed
        # Add more pattern matching here for other date formats
        
    except Exception as e:
        print(f"Error parsing date: {time_str}, error: {e}")
    
    return None

def fetch_html(url):

    # fake_headers = header.generate()
 
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to fetch page, status code: {response.status_code}")
        return response.status_code



def clean_markdown_newlines(text):
    # Ensure we only replace single \n inside sentences, not within lists/tables
    new_text =  re.sub(r'(?<!\n)\n(?![\n\-\*\|])', ' ', text)
    new_text = new_text.replace("** _", "**_")
    new_text = new_text.replace("_ **", "_**")
    return new_text



def process_markdown(markdown_text):
    # Split the text by code block delimiters
    parts = re.split(r'(```.*?```)', markdown_text, flags=re.DOTALL)
    
    result = []
    in_code_block = False
    
    for i, part in enumerate(parts):
        # Check if this part is a code block
        if part.startswith('```') and part.endswith('```'):
            # Keep code blocks unchanged
            result.append(part)
        else:
            # For text outside code blocks, replace multiple spaces with a single space
            processed_part = clean_markdown_newlines(re.sub(r' +', ' ', part))
            result.append(processed_part)
    
    return ''.join(result)


def html_to_markdown(html_content):
    converter = html2text.HTML2Text()
    converter.ignore_links = True  # Keep links
    converter.ignore_images = True  # Keep images
    converter.ignore_tables = False  # Keep tables
    return converter.handle(html_content)


def check_table_content(text):
    new_text = ""

    table_lines = []
    texts = text.split("\n")
    is_table = False

    for i,t in enumerate(texts):
        num_colons = t.count("|") + 1
        if num_colons > 1 and not is_table:
            # Look ahead to see if the next line is a table line
            if i < len(texts) - 1:
                next_line = texts[i+1]
                if next_line.count("|") + 1 == num_colons:

                    flag_table_divider = True
                    unique_chars = set(next_line)
                    for char in unique_chars:
                        if char not in [" ", "-", ":", "|"]:
                            flag_table_divider = False
                            
                    if flag_table_divider:
                        is_table = True
                        table_lines.append(t)
                        continue

        if num_colons > 1 and is_table:
            table_lines.append(t)
            continue


        # If we have a table, process it
        # If not, just add the text
        if len(table_lines) > 0:
            for line in table_lines:
                new_text += "| " + line + "|\n"
            new_text += "\n"
        table_lines = []
        is_table = False 
        new_text += t + "\n"

    if len(table_lines) > 0:
        for line in table_lines:
            new_text += "| " + line + "|\n"  
        new_text += "\n"  
    return new_text  


def fulltext_to_markdown(content):
    # Chuyển đổi HTML sang Markdown
    text = html_to_markdown(content)
    
    # Xử lý các ký tự không mong muốn
    text = check_table_content(text)
    text = process_markdown(text)
    
    return text



def process_a_page(object, func):
    time.sleep(1)
    url = object["link"]
    html = fetch_html(url)
    if html is not None:
        page = func(html)
        if page is not None:
            page["link"] = url
            return page
        else:
            print(f"Failed to parse page: {url}")
    return None



def process_a_page_and_save(object: Dict, func: Callable, output_dir: str, err_dir: str = None):
    page = process_a_page(object, func)
    if page is not None and page["time"] and page["content"]:
        with open(output_dir, "a", encoding='utf-8') as f:
            json.dump(page, f, ensure_ascii=False)
            f.write("\n")
    elif err_dir is not None:
        with open(err_dir, "a", encoding='utf-8') as f:
            json.dump(object, f, ensure_ascii=False)
            f.write("\n")



def crawler(pages_url, output_dir: str, err_dir: str = None, max_threads: int = 10, func: Callable=None):
    
    with ThreadPoolExecutor(max_threads) as executor:
        futures = [executor.submit(process_a_page_and_save, page_url, func, output_dir, err_dir) for page_url in pages_url]

        with tqdm(total=len(futures), desc="Processing Pages") as pbar:
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error processing {e}")
                pbar.update(1)
    
    # for page_url in pages_url:
    #     process_a_page_and_save(page_url, output_dir)

    print(f"Scraping completed. Saved to {output_dir}")




def runner(link_dir: str, output_dir: str, err_dir: str = None, max_threads: int = 10, func: Callable=None):
    done_urls = set()

    if os.path.exists(output_dir):
        with open(output_dir, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    page = json.loads(line)
                    done_urls.add(page["link"])
                except:
                    pass

    if os.path.exists(err_dir):
        with open(err_dir, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    page = json.loads(line)
                    done_urls.add(page["link"])
                except:
                    pass

    pages_url = []
    with open(link_dir, "r", encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                if data["link"] not in done_urls:
                    pages_url.append(data)
            except json.JSONDecodeError as e:
                print(f"WARNING: Skip error line")
    crawler(pages_url, output_dir, err_dir=err_dir, max_threads=max_threads, func=func)



def multithreaded_crawl(collection, parser_func, max_threads=4, limit=None):
    if limit:
        cursor = collection.find({
            "$and": [
                {"$or": [
                    {"content": {"$exists": False}},
                    {"content": None},
                    {"content": ""}
                ]},
                {"$or": [
                    {"is_err_link": {"$exists": False}},
                    {"is_err_link": False}
                ]}
            ]
        }).limit(limit)
    else:
        # Find all documents that need to be crawled
        cursor = collection.find({
            "$and": [
                {"$or": [
                    {"content": {"$exists": False}},
                    {"content": None},
                    {"content": ""}
                ]},
                {"$or": [
                    {"is_err_link": {"$exists": False}},
                    {"is_err_link": False}
                ]}
            ]
        })

    def worker(doc):
        url = doc.get("link")
        time.sleep(random.uniform(0.5, 1.5))
        html = fetch_html(url)

        if not isinstance(html, str):
            if html == 403:
                print(f"Error 403: Forbidden access to {url}")
                return
            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    # "time": parse_vietnamese_datetime(data["time"]),
                    "is_err_link": True
                }}
            )
            return
        try:
            data = parser_func(html)
            if data:
                collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {
                        "time": parse_vietnamese_datetime(data["time"]),
                        "content": data["content"],
                        "is_err_link": data["is_err_link"]
                    }}
                )
            else:
                collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {
                        "time": parse_vietnamese_datetime(data["time"]),
                        "is_err_link": True
                    }}
                )
                print(f"Error: No data returned for document {doc['_id']}")
                return
                
        except Exception as e:
            print(f"Error processing document {doc['_id']}: {e}")
            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    # "time": parse_vietnamese_datetime(data["time"]),
                    "is_err_link": True
                }}
            )
            return 

    docs = list(cursor)
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [executor.submit(worker, doc) for doc in docs]
        
        with tqdm(total=len(futures), desc="Crawling documents") as pbar:
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error: {e}")
                pbar.update(1)

    print("Completed multithreaded crawl.")

def multithreaded_crawl_bq(client, table, parser_func, max_threads=4, limit=None):
    if not client or not table or not isinstance(table, bigquery.Table):
        print("Invalid client or table.")
        return
    # print(f"Crawling: {table.project}.{table.dataset_id}.{table.table_id} ---")
    def fetch_pending_rows(table, limit=None):
        table_ref_str = f"`{table.project}.{table.dataset_id}.{table.table_id}`"
        query_str = f"""
        SELECT * FROM {table_ref_str}
        WHERE (content IS NULL OR content = "nan" OR content = "None")
        OR (is_err_link IS NULL
        OR is_err_link = 'False'
        OR is_err_link = 'nan')
        """
        if limit:
            query_str += f" LIMIT {limit}"
        print(f"Executing query to fetch pending rows")
        return client.query(query_str).to_dataframe()

    def process_row(row, parser_func):
        url = row['link']
        time.sleep(random.uniform(0.5, 1.5))

        html = fetch_html(url)

        result = {
            "link": row["link"],
            "is_err_link": True,#here
            "content": None,
            "time": None,
            "word_count" : 0,#note fix
        }

        if not isinstance(html, str):
            return result

        try:
            data = parser_func(html)
            if data:
                result["content"] = data.get("content")
                result["word_count"] = len(data.get("content", "").split()) #
                result["time"] = parse_vietnamese_datetime(data.get("time"))
                result["is_err_link"] = data.get("is_err_link", False)
        except Exception as e:
            print(f"[ERROR] Processing row failed: {e}")

        return result

    # Get unprocessed rows from BigQuery
    df = fetch_pending_rows(table, limit)
    print(f"Found {len(df)} rows to process from BigQuery")

    if df.empty:
        print("No data to process.")
        return

    updated_rows = []

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [executor.submit(process_row, row, parser_func) for _, row in df.iterrows()]
        with tqdm(total=len(futures), desc="Crawling documents") as pbar:
            for future in as_completed(futures):
                try:
                    result = future.result()
                    updated_rows.append(result)
                except Exception as e:
                    print(f"[THREAD ERROR] {e}")
                pbar.update(1)

    if updated_rows:
        result_df = pd.DataFrame(updated_rows)
        # if "time" in result_df.columns:
        #     result_df["time"] = result_df["time"].astype(str)
        if "time" in result_df.columns:
        # Convert to pandas datetime, errors='coerce' will turn invalid formats into NaT
            result_df["time"] = pd.to_datetime(result_df["time"], errors='coerce')
        if 'is_err_link' in result_df.columns:
            result_df['is_err_link'] = result_df['is_err_link'].astype(str)
        job = client.load_table_from_dataframe(
            result_df,
            table,
            job_config=bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
        )
        job.result()
        print(f"Updated {len(updated_rows)} rows in BigQuery.")
    else:
        print("No rows were updated.")