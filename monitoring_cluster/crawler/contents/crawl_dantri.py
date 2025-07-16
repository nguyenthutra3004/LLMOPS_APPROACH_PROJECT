import sys
from datetime import datetime
from bs4 import BeautifulSoup
sys.path.append("..")
from utils.utils import fetch_html, fulltext_to_markdown
from utils.utils import  connect_to_bigquery, multithreaded_crawl_bq
# ==== 2. Hàm phân tích nội dung bài viết ====
def parse_page_dantri(html):
    soup = BeautifulSoup(html, "html.parser")

    try:
        time_tag = soup.find("time", class_="author-time")
        time_text = time_tag.get_text(strip=True) if time_tag else ""
        content_div = soup.find("div", class_="singular-content")
        markdown = fulltext_to_markdown(content_div.prettify())
        # print(markdown)
        is_err_link = not content_div or not time_text
        return {
            "time": time_text,
            "content": markdown.strip(),
            "is_err_link": is_err_link  # True = có lỗi, False = không có lỗi
        }
    except Exception as e: # DNews
        time_tag = soup.find("time", class_="author-time")
        time_text = time_tag.get_text(strip=True) if time_tag else ""
#
        try:
            # Nếu dạng "22/05/2024 10:00"
            time_obj = datetime.strptime(time_text, "%d/%m/%Y %H:%M")
            time_iso = time_obj.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            # Nếu đã là ISO 8601 thì giữ nguyên
            time_iso = time_text
#
        content_div = soup.find("div", class_="e-magazine__body")
        
        if content_div:
            markdown = fulltext_to_markdown(content_div.prettify()).strip()
            is_err_link = False
        else:
            markdown = None
            is_err_link = True

        return {
            "time": time_iso,
            "content": markdown,
            "is_err_link": is_err_link  # True = có lỗi, False = không có lỗi
        }

if __name__ == "__main__":
    client, table = connect_to_bigquery("neusolution", "neusolution.json", "crawler_data", "links_dantri")
    multithreaded_crawl_bq(client, table, parse_page_dantri, max_threads=4,limit=100)