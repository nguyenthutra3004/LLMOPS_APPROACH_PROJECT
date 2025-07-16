from datetime import datetime
import pandas as pd
from google.cloud import bigquery
import os
import random


from utils.count import count_tokens_messages
from utils.utils import connect_to_mongo
from utils.clean_message import check_messages, prune_chinese


from pandas.api import types as ptypes
import json

from concurrent.futures import ThreadPoolExecutor, as_completed

current_dir = os.path.dirname(os.path.abspath(__file__))
credentials_path = os.path.join(current_dir, "neusolution.json")

from uuid import uuid4

# sft_huggingface
# id: INT (Required)
# source: STRING
# date_added: TIMESTAMP
# version: STRING
# messages: RECORD (repeated) 
#   role: STRING
#   messages: STRING


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path



def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


def convert_dict_to_dataframe(data, source, version=None):

    # messages is in format of list of dicts
    # data: list of dicts
    if isinstance(data, dict):
        data = [data]
    new_data = []

    # Prune data
    data = check_messages(prune_chinese(data))

    # Define worker function to process each item
    def process_item(item):
        messages = item.get('messages', [])
        # if isinstance(messages, list):
        #     messages = [json.dumps(message) for message in messages]
        # else:
        #     messages = [json.dumps(messages)]
            
        item['id'] = random.getrandbits(63)
        item['messages'] = messages
        item['source'] = source
        item['version'] = version
        item['token'] = count_tokens_messages(item.get('messages', []))
        item['date_added'] = datetime.now()
        return item

    # Process items in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=8) as executor:
        new_data = list(executor.map(process_item, data))

    return pd.DataFrame(new_data)



def load_df_to_bigquery(df, project_id, dataset_id, table_id):
    client = bigquery.Client(project=project_id)
    table_ref = f"{project_id}.{dataset_id}.{table_id}"
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,  # <-- Change here
    )
    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()  # Chờ cho đến khi job hoàn thành
    print(f"Loaded {job.output_rows} rows into {table_ref}.")

def dict_to_bigquery(data, source, project_id, dataset_id, table_id, version=None):
    df = convert_dict_to_dataframe(data, source, version)
    print(df.head())
    load_df_to_bigquery(df, project_id, dataset_id, table_id)

    del df


def batch_path_to_bigquery(path, source, project_id, dataset_id, table_id, version=None):
    # Đọc file JSON
    data = read_json_file(path)
    if version is None:
        version = source
    
    # Chuyển đổi dữ liệu thành DataFrame
    
    # batch of 1000 messages each. process in parallel

    data = [data[i:i + 1000] for i in range(0, len(data), 1000)]

    # with ThreadPoolExecutor(max_workers=5) as executor:
    #     futures = []
    #     for batch in data:
    #         future = executor.submit(dict_to_bigquery, batch, source, project_id, dataset_id, table_id, version)
    #         futures.append(future)

    #     for future in as_completed(futures):
    #         try:
    #             future.result()
    #         except Exception as e:
    #             print(f"Error processing batch: {e}")

    for batch in data:
        dict_to_bigquery(batch, source, project_id, dataset_id, table_id, version)

    
    # df = convert_dict_to_dataframe(data, source)
    # # Tải DataFrame lên BigQuery
    # load_df_to_bigquery(df, project_id, dataset_id, table_id)
    # del df

def fetch_all_messages(project_id, dataset_id, table_id):
    from google.cloud import bigquery
    client = bigquery.Client(project=project_id)
    query = f"""
        SELECT
            id,
            version,
            m.role,
            m.content
        FROM
            `{project_id}.{dataset_id}.{table_id}`,
            UNNEST(messages) AS m

        LIMIT 100
    """
    query_job = client.query(query)
    results = query_job.result()
    return [dict(row) for row in results]


def main():
    with open(credentials_path, 'r') as file:
        credentials = json.load(file)
    project_id = credentials['project_id']
    dataset_id = 'message'
    table_id = 'sft_huggingface'

    # Đường dẫn đến thư mục chứa các file JSON
    folder_path = '../../../ocr/messages/facebook_reasoning_vi_v2.json'

    batch_path_to_bigquery(folder_path, 'facebook_reasoning', project_id, dataset_id, table_id, 'facebook_reasoning_vi_v2')
    # batch_path_to_bigquery(folder_path, 'facebook_reasoning_vi', project_id, dataset_id, table_id)


if __name__ == "__main__":
    msgs = fetch_all_messages('neusolution', 'message', 'sft_huggingface')
    for msg in msgs:    
        print(msg)