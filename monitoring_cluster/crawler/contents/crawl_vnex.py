from bs4 import BeautifulSoup
import random
import time
import sys
sys.path.append("..")

from utils.utils import (
    fulltext_to_markdown,
    fetch_html,
    connect_to_bigquery
)


# Hàm parse nội dung trang VnExpress
def parse_page_vnex(url):
    soup = BeautifulSoup(url, "html.parser")
    content_section = soup.find("section", class_="section page-detail top-detail") \
                      or soup.find("section", class_="section page-detail detail-photo")
    if not content_section:
        return None
    time_tag = soup.find("span", class_="date")
    time_text = time_tag.get_text(strip=True) if time_tag else ""

    description_tag = content_section.find("p", class_="description")
    description = description_tag.get_text(strip=True) if description_tag else ""

    paragraphs = content_section.find_all("p", class_="Normal")
    article_text = "\n".join([
        p.get_text(strip=True) for p in paragraphs
        if not p.has_attr("style") or "text-align:right" not in p["style"]
    ])
    full_text = f"{description}\n\n{article_text}" if description else article_text
    text = fulltext_to_markdown(full_text.strip())
    is_err_link = not text or not time_text

    return {
        "time": time_text,
        "content": text,
        "is_err_link": is_err_link  # True = có lỗi, False = không có lỗi
    }

# Cào dữ liệu từng bài (đơn luồng)
def crawl_sequential(client, table, parser_func):
    query = """
        SELECT * FROM `neusolution.crawler_data.links_vnex`
        WHERE content IS NULL OR content = 'nan' OR content = ''

    """
            # LIMIT 20
    rows = client.query(query).result()
    for row in rows:
        url = row.link
        if not url:
            continue

        html = fetch_html(url)
        time.sleep(random.uniform(0.5, 2.0))
        if not html:
            continue

        try:
            parsed_data = parser_func(html)
            if parsed_data:
                updated_row = {
                    "link": url,
                    "time": parsed_data["time"],
                    "content": parsed_data["content"],
                    "is_err_link": str(parsed_data["is_err_link"])
                }

                # Gửi vào BigQuery (ghi đè bản cũ theo `link`)
                errors = client.insert_rows_json(table, [updated_row], row_ids=[url])
                if errors:
                    print(f"Error BigQuery: {errors}")
                else:
                    print(f"Update: {url}")
        except Exception as e:
            print(f"Error {url}: {e}")

# Main
if __name__ == "__main__":
    client, table = connect_to_bigquery("neusolution", "neusolution.json", "crawler_data", "links_vnex")

    crawl_sequential(client,table, parse_page_vnex)
