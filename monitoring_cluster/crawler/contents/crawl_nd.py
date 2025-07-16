from bs4 import BeautifulSoup
import sys 
sys.path.append("..")

from utils.utils import (
    fulltext_to_markdown,
    connect_to_bigquery,
    multithreaded_crawl_bq
)


# ==== 1. Kết nối MongoDB ====


def parse_page_nd(html):
    soup = BeautifulSoup(html, 'html.parser')
    body = soup.find('body')
    text_time = ""

    content = body.find('div', class_='main-content')
    if content is None:
        return None

    try:
        title  = body.find('h1', class_='article__title')
        tldr = content.find('div', class_='article__sapo')

        # content = content.find('div', class_='main-col')

        # Get time
        time = content.find('time', class_='time')
        if time is not None:

            text_time = time.text
            text_time = text_time.strip()
            time.decompose()

        content = content.find('div', class_='article__body')

        # img
        for img in content.find_all('img'):
            img.decompose()

        for figure in content.find_all('figure'):
            figure.decompose()

        for table in content.find_all('table', class_='picture'):
            table.decompose()

        text  = fulltext_to_markdown(content.prettify())
        
        title = fulltext_to_markdown(title.prettify())

        tldr = fulltext_to_markdown(tldr.prettify())

        time_text = text_time if text_time else ""
        full_text = f"{title}\n\n{tldr}\n\n{text}"
        is_err_link = not text or not time_text

        return {
            "time": time_text,
            "content": full_text.strip(),
            "is_err_link": is_err_link  # True = có lỗi, False = không có lỗi
        }
    except Exception as e:
        print(f"Error: {e}")
        return None

# ==== 4. Chạy chính ====

if __name__ == "__main__":
    client, table = connect_to_bigquery("neusolution", "neusolution.json", "crawler_data", "links_nd")
    multithreaded_crawl_bq(client, table, parse_page_nd, max_threads=4)
