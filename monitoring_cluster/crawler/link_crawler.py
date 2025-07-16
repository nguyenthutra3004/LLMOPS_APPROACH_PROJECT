from links import (
    dantri_link_crawler,
    nd_link_crawler_vi,
    nd_link_crawler_en,
    nd_link_crawler_cn,
    nd_link_crawler_fr,
    tg_link_crawler,
    vnet_link_crawler,
    vtc_link_crawler,
)
import concurrent.futures


# Mapping source names to their corresponding crawler functions
SOURCE_CRAWLER_MAP = {
    'dantri': dantri_link_crawler,
    'nd-vi': nd_link_crawler_vi,
    'nd-en': nd_link_crawler_en,
    'nd-cn': nd_link_crawler_cn,
    'nd-fr': nd_link_crawler_fr,
    'tg': tg_link_crawler,
    'vnet': vnet_link_crawler,
    'vtc': vtc_link_crawler,
}


def link_crawler(source='dantri', start=1, end=2):
    """MAIN FUNCTION TO CRAWL LINKS FROM DIFFERENT SOURCES"""
    crawler_func = SOURCE_CRAWLER_MAP.get(source)
    if crawler_func:
        crawler_func(start, end)
    else:
        valid_sources = ", ".join(SOURCE_CRAWLER_MAP.keys())
        print(f"[ERROR] Unknown source: {source}. Please choose from: {valid_sources}")


def crawl_all_link_parallel(start=1, end=2, sources=None):
    """Crawl links from multiple sources in parallel

    Args:
        start (int): Start page number
        end (int): End page number
        sources (list, optional): List of sources to crawl. If None, crawl all sources.
    """
    all_sources = list(SOURCE_CRAWLER_MAP.keys())

    if sources is None:
        sources = all_sources

    valid_sources = [s for s in sources if s in all_sources]
    invalid_sources = [s for s in sources if s not in all_sources]

    for source in invalid_sources:
        print(f"[WARNING] Unknown source: {source}. Skipping.")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_source = {
            executor.submit(link_crawler, source, start, end): source
            for source in valid_sources
        }

        for future in concurrent.futures.as_completed(future_to_source):
            source = future_to_source[future]
            try:
                future.result()
                print(f"[INFO] Successfully crawled {source}")
            except Exception as exc:
                print(f"[ERROR] Failed to crawl {source}: {exc}")


if __name__ == "__main__":
    # Crawl all sources in parallel
    crawl_all_link_parallel(start=1, end=2)

    # Or crawl specific sources
    # crawl_all_link_parallel(start=1, end=2, sources=['dantri', 'vnet', 'vtc'])
'''
***How the program works overall***

When the file is run, the program calls crawl_all_link_parallel(start=1, end=2).

This function retrieves all sources from SOURCE_CRAWLER_MAP (since sources=None).

The sources are checked for validity (in this case, all are valid).

Each source is assigned a thread to run the link_crawler function.

In the link_crawler function, the corresponding crawler function (e.g., dantri_link_crawler) is called to collect links from the start page to the end page.

The results of each thread are processed:

If successful, a success message is printed.
If it fails, an error message is printed.
'''