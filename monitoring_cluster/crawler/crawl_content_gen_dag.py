from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import sys

sys.path.append(os.path.dirname(__file__))

from link_crawler import crawl_all_link_parallel
from content_crawler import crawl_all_content_parallel
from generate_messages import rotate_generate_and_save_to_bigquery

# Default arguments for DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Configurable parameters
LINK_CRAWLER_PARAMS = {'start': 1, 'end': 2, 'sources': 'dantri'}
CONTENT_CRAWLER_PARAMS = {'max_threads': 4, 'limit': 10}
MESSAGE_GEN_PARAMS = { 'max_threads': 4, 'limit': 10}

# Wrapper functions
def run_task(func, **kwargs):
    params = kwargs.get('params', {})
    try:
        func(**params)
        print(f"[INFO] Task {func.__name__} completed successfully with params: {params}")
    except Exception as e:
        print(f"[ERROR] Task {func.__name__} failed with error: {e}")
        raise

# DAG definition
with DAG(
    dag_id='crawler_content_conversion_dag',
    default_args=default_args,
    description='DAG to crawl links, collect content, and generate messages',
    schedule_interval=None,
    catchup=False,
    start_date=datetime(2025, 1, 1),
) as dag:

    crawl_links = PythonOperator(
        task_id='crawl_links',
        python_callable=run_task,
        op_kwargs={'func': crawl_all_link_parallel},
        params=LINK_CRAWLER_PARAMS,
    )

    crawl_content = PythonOperator(
        task_id='crawl_content',
        python_callable=run_task,
        op_kwargs={'func': crawl_all_content_parallel},
        params=CONTENT_CRAWLER_PARAMS,
    )

    generate_messages = PythonOperator(
        task_id='generate_messages',
        python_callable=run_task,
        op_kwargs={'func': rotate_generate_and_save_to_bigquery},
        params=MESSAGE_GEN_PARAMS,
    )

    # Define task dependencies
    crawl_links >> crawl_content >> generate_messages
