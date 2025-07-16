from bs4 import BeautifulSoup
import sys 
sys.path.append("..")
from utils.utils import (
    fulltext_to_markdown,
    connect_to_bigquery,
    multithreaded_crawl_bq
)

# ==== 2. Hàm phân tích nội dung bài viết ====
def parse_page_vtc(html):
    soup = BeautifulSoup(html, "html.parser")
    time_tag = soup.find("span", class_=lambda x: x and "time-update" in x)
    time_text = time_tag.get_text(strip=True) if time_tag else ""
    content_paragraphs = soup.find("div", class_="content-wrapper pt5 mt5 font18 gray-31 bor-4top-e5 lh-1-5")
    text = fulltext_to_markdown(content_paragraphs.prettify())
    is_err_link = not text or not time_text
    return {
        "time": time_text,
        "content": text.strip(),
        "is_err_link": is_err_link  # True = có lỗi, False = không có lỗi
    }


if __name__ == "__main__":
    client, table = connect_to_bigquery("neusolution", "neusolution.json", "crawler_data", "links_vtc")
    multithreaded_crawl_bq(client, table, parse_page_vtc, max_threads=4,limit=100)


    