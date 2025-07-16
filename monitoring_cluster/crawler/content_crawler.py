from contents import (
    parse_page_dantri,
    parse_page_nd,
    #parse_page_tg,
    parse_page_vnet,
    parse_page_vtc,
)

from dotenv import load_dotenv
from pathlib import Path

# Get the directory of the current file
env_path = Path(__file__).parent / '.env'

# Load the .env file
load_dotenv(dotenv_path=env_path)

from utils.utils import multithreaded_crawl_bq
from utils.utils import connect_to_bigquery
import concurrent.futures


# Mapping sources to their parser functions
SOURCE_PARSER_MAP = {
    'dantri': parse_page_dantri,
    'nd': parse_page_nd,
    # 'tg': parse_page_tg,
    'vnet': parse_page_vnet,
    'vtc': parse_page_vtc,
}


def content_crawler(source='dantri', max_threads=4, limit = 10):
    """Main function to crawl content from a specific source."""
    parser_func = SOURCE_PARSER_MAP.get(source)

    if not parser_func:
        valid_sources = ', '.join(SOURCE_PARSER_MAP.keys())
        print(f"[ERROR] Unknown source: {source}. Please choose from: {valid_sources}")
        return

    client, table = connect_to_bigquery(
        dataset_name='crawler_data',
        table_name=f'links_{source}'
    )
    if not client or not table:
        print(f"[ERROR] Failed to connect to BigQuery for source: {source}")
        return
    multithreaded_crawl_bq(client=client, table=table, parser_func=parser_func, max_threads=max_threads, limit=limit)

def crawl_all_content_parallel(max_threads=4, sources=None, limit=10):
    """Crawl content from multiple sources in parallel.

    Args:
        max_threads (int): Max number of threads per source.
        sources (list): List of sources to crawl. If None, crawl all.
    """
    
    all_sources = list(SOURCE_PARSER_MAP.keys())

    if sources is None:
        sources = all_sources

    valid_sources = [s for s in sources if s in all_sources]
    invalid_sources = [s for s in sources if s not in all_sources]

    for source in invalid_sources:
        print(f"[WARNING] Unknown source: {source}. Skipping.")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_source = {
            executor.submit(content_crawler, source, max_threads, limit): source
            for source in valid_sources
        }

        for future in concurrent.futures.as_completed(future_to_source):
            source = future_to_source[future]
            try:
                future.result()
                print(f"[INFO] Successfully crawled content from {source}")
            except Exception as exc:
                print(f"[ERROR] Error crawling content from {source}: {exc}")


if __name__ == "__main__":
    crawl_all_content_parallel(max_threads=4)
    # Or: content_crawler('dantri')
#