from bs4 import BeautifulSoup
import pymongo
import time
import sys 
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
sys.path.append("..")

from utils.utils import (
    fetch_html,
    fulltext_to_markdown,
    parse_vietnamese_datetime,
    connect_to_bigquery,
    multithreaded_crawl_bq
)

# ==== 2. Hàm phân tích nội dung bài viết ====


def parse_page_vnet(html):
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")
    # Need first container__left not-pl class
    content = body.find("div", class_="main-v1 bg-white")

    if content is None:
        return None
    
    time = content.find("div", class_="bread-crumb-detail__time") 
    content = content.find("div", class_="content-detail")
    if content is None:
        return None

    # Remove author in author tag
    author = content.find("div", class_="article-detail-author-wrapper")
    if author:
        author.decompose()

    # Remove share button
    share = content.find("div", class_="vnn-share-social share-social")
    if share:
        share.decompose()

    # Remove all the img and figure tags
    for img in content.find_all("img"):
        img.decompose()
    
    for figure in content.find_all("figure"):
        figure.decompose()

    # Remove em tag
    for center in content.find_all("p", class_="text-align: center;"):
        for em in center.find_all("em"):
            em.decompose()

    # Remove suggested articles
    for arg in content.find_all("article"):
        arg.decompose()
    
    text = fulltext_to_markdown(content.prettify())
    time_text = time.get_text(strip=True) if time else ""
    is_err_link = not text or not time_text

    return {
        "time": time_text,
        "content": text.strip(),
        "is_err_link": is_err_link  # True = có lỗi, False = không có lỗi
    }

# ==== 4. Khởi chạy chính ====

if __name__ == "__main__":

    client, table = connect_to_bigquery("neusolution", "neusolution.json", "crawler_data", "links_vnet")
    multithreaded_crawl_bq(client, table, parse_page_vnet, max_threads=4,limit=100)

    