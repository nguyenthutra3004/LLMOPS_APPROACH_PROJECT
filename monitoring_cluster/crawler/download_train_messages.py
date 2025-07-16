from google.cloud import bigquery
import math
import os
import pandas as pd
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
credentials_path = os.path.join(current_dir, "neusolution.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

class BigQueryChunkedDownloader:
    def __init__(self, project_id, dataset_id, table_id, chunk_size=5000, hard_limit=1000000):
        self.client = bigquery.Client(project=project_id)
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.chunk_size = chunk_size
        self.hard_limit = hard_limit



    def _get_total_row_count(self):
        query = f"""
            SELECT COUNT(*) AS total
            FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
        """
        return self.client.query(query).result().to_dataframe().iloc[0]["total"]

    def fetch_chunks(self, order_by_column="id"):
        all_rows = self._get_total_row_count()


        total_rows = min(all_rows, self.hard_limit)
        rows_per_chunk = max(1, self.chunk_size)
        num_chunks = math.ceil(total_rows / rows_per_chunk)

        print(f"Total selected rows: {total_rows} in {all_rows} rows")
        print(f"Fetching in {num_chunks} chunks of ~{rows_per_chunk} rows each...")

        for chunk in range(num_chunks):
            start = chunk * rows_per_chunk + 1
            end = start + rows_per_chunk - 1
            query = f"""
    WITH outer_rows AS (
      SELECT
        ROW_NUMBER() OVER (ORDER BY {order_by_column}) AS rn,
        id, version, messages
      FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
    )
    SELECT *
    FROM outer_rows
    WHERE rn BETWEEN {start} AND {end}
            """
            df = self.client.query(query).result()
            result = [dict(row) for row in df]
            print(result)
            yield result


if __name__ == "__main__":
    project_id = "neusolution"
    dataset_id = "message"
    table_id = "sft_huggingface"
    chunk_size = 5
    hard_limit = 20

    downloader = BigQueryChunkedDownloader(project_id, dataset_id, table_id, chunk_size, hard_limit)

    # Write to jsonl file directly in the loop to avoid memory issues
    with open("output.jsonl", 'w') as f:
        total_rows = 0
        for chunk in downloader.fetch_chunks(order_by_column="date_added"):
            print(f"Fetched chunk with {len(chunk)} rows")
            for row in chunk:
                f.write(json.dumps(row) + '\n')
            total_rows += len(chunk)
        print(f"Total fetched rows: {total_rows}")
    print(f"Data written to output.jsonl")